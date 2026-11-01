"""apply-graph-web --career ../../career [--backend claude-code] [--port 5181]

A local page for running the graph: pick a posting, watch each node finish over SSE, then approve
or send back the draft at the interrupt. Runs write to <career>/_graph-runs/<run id>/, never into
the role folder, and checkpoint to one SQLite file there, so a parked run survives a restart.

  POST /api/runs               {"job": "<role folder>"}            -> SSE, one event per finished node
  POST /api/runs/{id}/resume   {"approved": bool, "note": str}     -> SSE, continues from the interrupt
  GET  /api/runs/{id}                                              -> current snapshot (for a reload)
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import time
from collections.abc import Iterator
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command
from pydantic import BaseModel
from pydantic_core import to_jsonable_python

from .graph import MAX_DRAFTS, build_graph
from .llm import LLM, ClaudeCodeLLM, ClaudeLLM
from .state import SERDE

PAGE = Path(__file__).with_name("static") / "index.html"
JD = "03-Job-Description.md"
HIDDEN = {"job_text", "facts_text"}  # large inputs the page never needs back


class StartRun(BaseModel):
    job: str


class Resume(BaseModel):
    approved: bool
    note: str = ""


def create_app(llm: LLM, career: Path, checkpointer=None) -> FastAPI:
    runs_dir = career / "_graph-runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    if checkpointer is None:
        conn = sqlite3.connect(runs_dir / ".graph.sqlite", check_same_thread=False)
        checkpointer = SqliteSaver(conn, serde=SERDE)
    graph = build_graph(llm, checkpointer=checkpointer)
    app = FastAPI(title="apply-graph")

    def config(run_id: str) -> dict:
        return {"configurable": {"thread_id": run_id}}

    def shape(run_id: str, values: dict, next_nodes) -> dict:
        values = {k: v for k, v in values.items() if k not in HIDDEN}
        return {"run_id": run_id, "next": list(next_nodes), "state": to_jsonable_python(values)}

    def snapshot(run_id: str) -> dict:
        snap = graph.get_state(config(run_id))
        return shape(run_id, snap.values, snap.next)

    def sse(event: dict) -> str:
        event["at"] = round(time.time(), 2)  # server clock, so the page can time each node
        return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    def stream(run_id: str, payload) -> Iterator[str]:
        # A sync generator: Starlette runs it in a worker thread, so graph.stream can block on the model.
        # "updates" says which node finished; the "checkpoints" event right after it carries the state
        # with that node applied and the next node. get_state() at the update would still be one step
        # behind, because the checkpoint is saved after the update is emitted.
        yield sse({"type": "start", **snapshot(run_id)})
        finished = None
        try:
            for mode, chunk in graph.stream(payload, config(run_id), stream_mode=["updates", "checkpoints"]):
                if mode == "updates" and "__interrupt__" in chunk:
                    yield sse({"type": "interrupt", "node": "__interrupt__", **snapshot(run_id)})
                elif mode == "updates":
                    finished = next(iter(chunk))
                elif finished:
                    state = shape(run_id, chunk["values"], chunk["next"])
                    yield sse({"type": "step", "node": finished, **state})
                    finished = None
        except Exception as e:  # surface model / CLI failures on the page instead of a dead stream
            yield sse({"type": "error", "message": f"{type(e).__name__}: {e}", **snapshot(run_id)})
            return
        yield sse({"type": "end", **snapshot(run_id)})

    def sse_response(gen: Iterator[str]) -> StreamingResponse:
        # X-Accel-Buffering stops a proxy from batching the events into one late response
        headers = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
        return StreamingResponse(gen, media_type="text/event-stream", headers=headers)

    @app.get("/", response_class=HTMLResponse)
    def page() -> str:
        return PAGE.read_text(encoding="utf-8")

    @app.get("/api/meta")
    def meta() -> dict:
        return {"backend": type(llm).__name__, "max_drafts": MAX_DRAFTS, "runs_dir": str(runs_dir)}

    @app.get("/api/jobs")
    def jobs() -> list[dict]:
        # role folders are dated (YYYY-MM-DD-Company-Role); this skips templates like application/
        found = [d for d in career.iterdir() if d.is_dir() and d.name[:1].isdigit() and (d / JD).is_file()]
        return [{"id": d.name} for d in sorted(found, key=lambda d: d.name, reverse=True)]

    @app.get("/api/runs")
    def runs() -> list[dict]:
        out = []
        for d in sorted((d for d in runs_dir.iterdir() if d.is_dir()), key=lambda d: d.name, reverse=True):
            s = snapshot(d.name)
            if s["state"]:
                out.append({"run_id": d.name, "next": s["next"], "status": s["state"].get("status")})
        return out

    @app.get("/api/runs/{run_id}")
    def run(run_id: str) -> dict:
        s = snapshot(run_id)
        if not s["state"]:
            raise HTTPException(404, "no such run")
        return s

    @app.post("/api/runs")
    def start(body: StartRun) -> StreamingResponse:
        role = career / body.job
        if not body.job[:1].isdigit() or role.parent != career or not (role / JD).is_file():
            raise HTTPException(404, f"no {JD} in {body.job}")
        run_id = f"{time.strftime('%Y%m%d-%H%M%S')}-{body.job}"
        out = runs_dir / run_id
        out.mkdir(parents=True)
        inputs = {
            "job_text": (role / JD).read_text(encoding="utf-8"),
            "facts_text": (career / "facts.md").read_text(encoding="utf-8"),
            "out_dir": str(out),
        }
        return sse_response(stream(run_id, inputs))

    @app.post("/api/runs/{run_id}/resume")
    def resume(run_id: str, body: Resume) -> StreamingResponse:
        if graph.get_state(config(run_id)).next != ("approve",):
            raise HTTPException(409, "run is not waiting for approval")
        return sse_response(stream(run_id, Command(resume=body.model_dump())))

    return app


def main(argv: list[str] | None = None) -> None:
    import uvicorn

    p = argparse.ArgumentParser(prog="apply-graph-web")
    p.add_argument("--career", type=Path, required=True, help="folder with facts.md and one folder per role")
    p.add_argument("--backend", choices=["api", "claude-code"], default="claude-code")
    p.add_argument("--port", type=int, default=5181)
    a = p.parse_args(argv)
    llm = ClaudeCodeLLM() if a.backend == "claude-code" else ClaudeLLM()
    uvicorn.run(create_app(llm, a.career.resolve()), host="127.0.0.1", port=a.port)


if __name__ == "__main__":
    main()
