"""apply-graph-history --db career/_graph-runs/.graph.sqlite --thread <run id> [--field draft]

Walks one run's checkpoints oldest to newest and prints which state fields each step changed.
Nothing runs: no model calls, no files written. The checkpoint_id on each line is what you pass in
config["configurable"]["checkpoint_id"] to read that step again or fork the run from it.
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver

from .graph import build_graph
from .state import SERDE


def changes(graph, config: dict) -> list[dict]:
    """One entry per checkpoint, oldest first: the node(s) that produced it and the fields they changed.

    get_state_history yields newest first. A checkpoint does not name the node that wrote it, but the
    checkpoint before it says which node(s) were due next, so that is who ran in between. The first
    checkpoint is the empty start; the second holds the run's inputs.
    """
    out = []
    prev_values: dict = {}
    prev_next: tuple = ()
    for snap in reversed(list(graph.get_state_history(config))):
        source = snap.metadata.get("source")
        node = "+".join(prev_next) or source  # "input" for the first two checkpoints
        # a missing key and None read the same to every node, so writing None over nothing is no change
        changed = {k: v for k, v in snap.values.items() if prev_values.get(k) != v}
        out.append(
            {
                "step": snap.metadata.get("step"),
                "node": node,
                "changed": changed,
                "next": snap.next,
                "checkpoint_id": snap.config["configurable"]["checkpoint_id"],
            }
        )
        prev_values, prev_next = snap.values, snap.next
    return out


def preview(value, width: int = 70) -> str:
    if isinstance(value, list) and value:  # append-only fields like log: the new entry is what changed
        return f"[{len(value)}] ... {preview(value[-1], width - 10)}"
    text = value.model_dump_json() if hasattr(value, "model_dump_json") else repr(value)
    text = " ".join(text.split())
    return text if len(text) <= width else text[: width - 3] + "..."


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="apply-graph-history")
    p.add_argument("--db", type=Path, required=True, help="the run's .graph.sqlite")
    p.add_argument("--thread", required=True, help="run id (web) or --thread / --out folder name (CLI)")
    p.add_argument("--field", help="only show steps that changed this field, with its value")
    a = p.parse_args(argv)

    conn = sqlite3.connect(a.db, check_same_thread=False)
    # llm=None: get_state_history only reads checkpoints, no node runs
    graph = build_graph(None, checkpointer=SqliteSaver(conn, serde=SERDE))
    steps = changes(graph, {"configurable": {"thread_id": a.thread}})
    if not steps:
        raise SystemExit(f"no checkpoints for thread {a.thread!r} in {a.db}")

    for s in steps:
        fields = [f for f in s["changed"] if f not in {"job_text", "facts_text"}]
        if a.field and a.field not in s["changed"]:
            continue
        nxt = ",".join(s["next"]) or "END"
        print(f"step {s['step']:>2}  {s['node']:<17} -> {nxt:<17} {s['checkpoint_id']}")
        if a.field:
            print(f"          {a.field} = {preview(s['changed'][a.field])}")
        elif fields:
            print(f"          changed: {', '.join(fields)}")


if __name__ == "__main__":
    main()
