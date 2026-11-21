"""prep-graph --invite email.txt --job 03-Job-Description.md --facts facts.md --out <role folder>
             [--research research.txt] [--thread ID] [--backend claude-code]

research.txt: the company site / blog text and the interviewer's public profile, saved by you
(the graph never logs in or browses). Output: <out>/04-Interview-Prep.graph.md.
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from .llm import ClaudeCodeLLM, ClaudeLLM
from .prep import build_prep_graph
from .prep_state import SERDE


def ask(payload: dict) -> dict:
    if payload["ask"] == "compact":
        print(
            "\nClosed applications that can shrink to one archive line (deleted files cannot be recovered):"
        )
        approved = []
        for c in payload["candidates"]:
            plan = ", ".join(f"{f['name']}={f['action']}" for f in c["files"])
            if input(f"- {c['folder']} ({c['status']}): {plan}\n  compact? [y/N] ").strip().lower() != "y":
                continue
            lesson = input("  one-line lesson (or empty): ").strip() if c["interviewed"] else ""
            approved.append({"folder": c["folder"], "lesson": lesson})
        return {"approved": approved}
    if payload["ask"] == "stage":
        print("\nCould not verify the stage:", *payload["problems"], sep="\n- ")
        return {"stage": input("Stage? [SCREEN/OA/TECH/ONSITE/OFFER/REJECTED/APPLIED]: ").strip()}
    confirmed = []
    if payload.get("proposals"):
        print("\nFound in your other files (not in facts.md yet). Confirm only what is true:")
        for e in payload["proposals"]:
            print(f"- {e['gap']}\n  {e['source']} ({e['strength']}): {e['quote']}\n  -> {e['answer']}")
            if input("  confirm? [y/N] ").strip().lower() == "y":
                confirmed.append(e["answer"])
    print("\nStill open. Answer with a true fact, or press Enter to leave it as a gap.")
    answers = []
    for gap in payload["gaps"]:
        a = input(f"- {gap}\n  > ").strip()
        if a:
            answers.append(a)
    return {"answers": answers, "confirmed": confirmed}


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="prep-graph")
    p.add_argument("--invite", type=Path, required=True)
    p.add_argument("--job", type=Path, required=True)
    p.add_argument("--facts", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--research", type=Path)
    p.add_argument(
        "--career", type=Path, help="career folder: enables the compact step for closed applications"
    )
    p.add_argument("--thread", default=None)
    p.add_argument("--backend", choices=["api", "claude-code"], default="api")
    a = p.parse_args(argv)

    a.out.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(a.out / ".prep-graph.sqlite", check_same_thread=False)
    llm = ClaudeCodeLLM() if a.backend == "claude-code" else ClaudeLLM()
    graph = build_prep_graph(llm, checkpointer=SqliteSaver(conn, serde=SERDE))
    config = {"configurable": {"thread_id": a.thread or a.out.name}}

    snapshot = graph.get_state(config)
    if snapshot.next:
        result = graph.invoke(Command(resume=ask(snapshot.interrupts[0].value)), config)
    else:
        read = lambda f: f.read_text(encoding="utf-8") if f else ""  # noqa: E731
        inputs = {
            "invite_text": read(a.invite),
            "job_text": read(a.job),
            "facts_text": read(a.facts),
            "research_text": read(a.research),
            "out_dir": str(a.out),
            **({"career_dir": str(a.career)} if a.career else {}),
            "sources": {
                n: (a.career / n).read_text(encoding="utf-8")
                for n in ("stories.md", "blocks.md")
                if a.career and (a.career / n).is_file()
            },
        }
        result = graph.invoke(inputs, config)
    while "__interrupt__" in result:
        result = graph.invoke(Command(resume=ask(result["__interrupt__"][0].value)), config)
    print(f"\n{result['verdict']}", *result.get("reasons", []), sep="\n- ")
    if result["verdict"] != "STOPPED":
        print(f"-> {a.out / '04-Interview-Prep.graph.md'}")


if __name__ == "__main__":
    main()
