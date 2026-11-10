#!/usr/bin/env python3
"""Integrity gate for a pasted or saved job posting — the same guard jobs-mcp runs on fetched ones.

    python scripts/posting-guard.py posting.html                 # report; cleaned text to stdout
    python scripts/posting-guard.py raw.txt --out clean.txt      # write the cleaned text
    python scripts/posting-guard.py career/<folder>/03-Job-Description.md   # scans its ## Raw posting
    pbpaste | python scripts/posting-guard.py -                  # stdin
    python scripts/posting-guard.py --json posting.html          # machine-readable report

Removes hidden HTML and invisible characters, decodes text spelled in invisible characters, and
quotes instruction-shaped lines (never removes them). The first line of output is the one-line
verdict the skills open their analysis with. Pasted text keeps invisible Unicode even though copy
and paste drops hidden HTML, so pasted postings are worth checking too.

Exit status: 0 clean, 1 flagged, 2 usage error. Stdlib only; the guard lives in
mcp/jobs-mcp/jobs_mcp/guard.py.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "mcp" / "jobs-mcp"))
from jobs_mcp.guard import compact, guard  # noqa: E402


def read_input(src: str) -> tuple[str, str]:
    if src == "-":
        return sys.stdin.read(), "stdin"
    p = Path(src)
    text = p.read_text(encoding="utf-8")
    if p.suffix.lower() == ".md":
        raw = re.search(r"^## Raw posting\s*\n(.*?)(?=^## |\Z)", text, flags=re.M | re.S)
        if raw:
            return raw.group(1), f"{p} § Raw posting"
    return text, str(p)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("src", help="posting file (.html / .txt / .md) or - for stdin")
    ap.add_argument("--out", type=Path, help="write the cleaned text here instead of stdout")
    ap.add_argument("--json", action="store_true", help="print the report as JSON")
    ap.add_argument("--html", action=argparse.BooleanOptionalAction, default=None, help="force HTML / text")
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    try:
        raw, label = read_input(a.src)
    except OSError as e:
        print(f"posting-guard: {e}", file=sys.stderr)
        return 2
    text, report = guard(raw, is_html=a.html)

    if a.json:
        print(json.dumps({"source": label, **compact(report)}, ensure_ascii=False, indent=2))
    else:
        print(f"posting-guard: {report['verdict']}  ({label})")
        for title, key in (
            ("hidden", "hidden_blocks"),
            ("invisible text", "invisible_text"),
            ("instruction-shaped", "instruction_lines"),
            ("hidden-only url", "hidden_urls"),
            ("look-alike", "mixed_script"),
        ):
            for item in report[key]:
                print(f"  {title:<18} {item}")
        if report["invisible"]:
            counts = ", ".join(f"{k} {v}" for k, v in sorted(report["invisible"].items()))
            print(f"  {'removed chars':<18} {counts}")
    if a.out:
        a.out.write_text(text + "\n", encoding="utf-8")
    elif not a.json:
        print("\n" + text)
    return 0 if report["verdict"] == "clean" else 1


if __name__ == "__main__":
    sys.exit(main())
