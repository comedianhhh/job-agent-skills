"""Reuse scripts/check-trace.py (the deterministic number gate) instead of re-implementing it."""

from __future__ import annotations

import importlib.util
from functools import cache
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check-trace.py"


@cache
def _module():
    spec = importlib.util.spec_from_file_location("check_trace", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def check(letter: Path, facts_text: str) -> list[dict]:
    return _module().check([letter], [facts_text])
