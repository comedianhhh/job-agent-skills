"""Per-node token and time accounting.

A `Recorder` opens one span per node run; `TracedLLM` adds each model call's usage to whichever span
is open. Nodes that call no model (trace_check, record) still get a span with their wall time.
One Recorder and one LLM per run: usage is read off the LLM after each call, so a shared LLM across
threads would mix runs up.
"""

from __future__ import annotations

import math
import time
from collections import defaultdict
from contextlib import contextmanager
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

USAGE_KEYS = ("input_tokens", "output_tokens", "cost_usd")


class Recorder:
    def __init__(self) -> None:
        self.spans: list[dict] = []
        self._open: dict | None = None

    @contextmanager
    def node(self, name: str):
        span = {"node": name, "ms": 0, "calls": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}
        prev, self._open = self._open, span
        t0 = time.perf_counter()
        try:
            yield span
        finally:
            # approve raises GraphInterrupt to pause; its span still counts (it is how long the node took)
            span["ms"] = round((time.perf_counter() - t0) * 1000)
            self._open = prev
            self.spans.append(span)

    def add_usage(self, usage: dict | None) -> None:
        if self._open is None:
            return
        self._open["calls"] += 1
        for k in USAGE_KEYS:
            self._open[k] += (usage or {}).get(k) or 0


class TracedLLM:
    """Wraps any LLM; after each parse, books `llm.last_usage` (if the backend sets it) to the open span."""

    def __init__(self, llm, recorder: Recorder) -> None:
        self.llm = llm
        self.recorder = recorder

    def parse(self, system: str, user: str, schema: type[T]) -> T:
        out = self.llm.parse(system, user, schema)
        self.recorder.add_usage(getattr(self.llm, "last_usage", None))
        return out


def p95(values: list[float]) -> float:
    if not values:
        return 0
    s = sorted(values)
    return s[min(len(s) - 1, math.ceil(0.95 * len(s)) - 1)]


def per_node(spans: list[dict]) -> list[dict]:
    """Aggregate spans from many runs: one row per node, in first-seen order."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for s in spans:
        groups[s["node"]].append(s)
    rows = []
    for node, ss in groups.items():
        n = len(ss)
        ms = [s["ms"] for s in ss]
        rows.append(
            {
                "node": node,
                "runs": n,
                "calls": sum(s["calls"] for s in ss),
                "avg_in": round(sum(s["input_tokens"] for s in ss) / n),
                "avg_out": round(sum(s["output_tokens"] for s in ss) / n),
                "avg_ms": round(sum(ms) / n),
                "p95_ms": round(p95(ms)),
                "cost_usd": round(sum(s["cost_usd"] for s in ss), 4),
            }
        )
    return rows
