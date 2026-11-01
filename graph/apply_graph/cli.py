"""apply-graph --job JD.md --facts facts.md --out career/2026-11-01-Acme-Role [--thread ID]
                   [--backend claude-code]

Checkpoints go to <out>/.graph.sqlite. Ctrl-C at the approval prompt leaves the run parked there;
run the same command again with the same --thread to pick it back up.
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from .graph import build_graph
from .llm import ClaudeCodeLLM, ClaudeLLM
from .state import SERDE


def ask(payload: dict) -> dict:
    print("\n--- draft ---\n" + payload["draft"] + "\n-------------")
    reply = input("Approve? [y = yes / text = redraft with this note / empty = reject]: ").strip()
    return {"approved": True} if reply.lower() in {"y", "yes"} else {"approved": False, "note": reply}


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="apply-graph")
    p.add_argument("--job", type=Path, required=True)
    p.add_argument("--facts", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--thread", default=None, help="defaults to the --out folder name")
    p.add_argument(
        "--backend",
        choices=["api", "claude-code"],
        default="api",
        help="api: Anthropic SDK (needs ANTHROPIC_API_KEY); claude-code: the logged-in `claude` CLI",
    )
    a = p.parse_args(argv)

    a.out.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(a.out / ".graph.sqlite", check_same_thread=False)
    llm = ClaudeCodeLLM() if a.backend == "claude-code" else ClaudeLLM()
    graph = build_graph(llm, checkpointer=SqliteSaver(conn, serde=SERDE))
    config = {"configurable": {"thread_id": a.thread or a.out.name}}

    snapshot = graph.get_state(config)
    if snapshot.next:  # parked at an interrupt from an earlier run
        result = graph.invoke(Command(resume=ask(snapshot.interrupts[0].value)), config)
    else:
        inputs = {
            "job_text": a.job.read_text(encoding="utf-8"),
            "facts_text": a.facts.read_text(encoding="utf-8"),
            "out_dir": str(a.out),
        }
        result = graph.invoke(inputs, config)
    while "__interrupt__" in result:
        result = graph.invoke(Command(resume=ask(result["__interrupt__"][0].value)), config)
    print(f"\n{result['status']} -> {a.out / 'README.md'}")


if __name__ == "__main__":
    main()
