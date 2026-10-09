#!/usr/bin/env python3
"""Deterministic trace gate: every number in an outgoing document must exist in facts.md.

    python scripts/check-trace.py career/2026-10-04-Acme-Backend/          # resume + cover letter
    python scripts/check-trace.py career/blocks.md career/stories.md       # derived files vs. the root
    python scripts/check-trace.py --facts career/facts.md --json <paths>   # machine-readable

The skills already tell the model "every line traces to a fact". This is the part that does not
depend on the model: it fails on leftover TODO / [TBD] markers and on any number (75%, 3x, 256,
4.5) that cannot be found in facts.md. It cannot judge wording or ownership; it catches the
fabricated-metric class of error, which is the one an interviewer asks about first.

Exit status: 0 clean, 1 untraced numbers or markers found, 2 usage error. Stdlib only.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

MARKERS = re.compile(r"\bTODO\b|\[TBD\]|\bTBD\b")
# A number with an optional unit that changes its meaning: 75% / 3x / 3× / 10k / 2M / 4.5★ / 120+
NUMBER = re.compile(
    r"(?<![\w.])(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s?(%|percent\b|[x×](?![a-z])|[kKM]\b|\+|★)?"
)
WORDNUM = {"percent": "%", "×": "x", "★": ""}

# Text that carries numbers but no claims: contact details, links, dates, versions.
NOISE = [
    re.compile(r"\S+@\S+"),  # email
    re.compile(r"https?://\S+|\b[\w.-]+\.(?:com|io|ai|dev|org|net|app|co)(?:/\S*)?"),  # urls
    re.compile(r"\+?\d[\d\s().-]{8,}\d"),  # phone numbers
    re.compile(r"\b[A-Z]\d[A-Z]\s?\d[A-Z]\d\b"),  # Canadian postal code
    re.compile(r"\b(?:0?[1-9]|1[0-2])/(?:19|20)\d{2}\b"),  # 05/2025
    re.compile(r"\b(?:19|20)\d{2}\s?[-–—]\s?(?:(?:19|20)\d{2}|present)\b", re.I),  # 2023 – 2024
    re.compile(
        r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+(?:\d{1,2},?\s+)?(?:19|20)\d{2}\b",
        re.I,
    ),
    re.compile(r"(?<![\d,.])(?:19|20)\d{2}(?![\d%x×])"),  # bare years
    re.compile(r"\b\d{4}-\d{2}(?:-\d{2})?\b"),  # ISO dates
    re.compile(r"\bv?\d+\.\d+\.\d+\w*"),  # semver
    re.compile(r"\d+\s?(?:词|字)"),  # word-count notes in blocks.md ("≤ 31 词"), not claims
    re.compile(r"^#{1,6}\s*(?:S|§)?\d+(?:\.\d+)*\.?", re.M),  # heading numbers: "## 13.", "### 3.2", "## S19"
    re.compile(r"\d+(?:\.\d+)?\s?[x×]\s?10\S*"),  # scientific notation: 2×10⁻¹⁰
    # framework / platform versions: React 19/18, Next.js 16, Unity 6, Python 3.12, iOS 17, C++17, ES2022
    re.compile(
        r"(?:\b(?:React|Next\.js|Node(?:\.js)?|Vue|Angular|Svelte|Unity|Unreal(?:\s+Engine)?|UE|Python|Java|"
        r"Kotlin|Swift|iOS|Android|Postgres(?:QL)?|MySQL|Redis|Django|Rails|Spring(?:\s+Boot)?|Vite|"
        r"Tailwind(?:\s+CSS)?|TypeScript|OpenGL|DirectX|Vulkan|Gemini|GPT|Claude|Llama)|C\+\+|\.NET|\bES)"
        r"[\s-]?v?\d+(?:\.\d+)*(?:/\d+)*"
    ),
]


def strip_html(s: str) -> str:
    s = re.sub(r"<(head|header|script|style)\b.*?</\1>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    return html.unescape(s)


def document_text(path: Path) -> str:
    raw = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".html", ".htm"}:
        return strip_html(raw)
    if path.name.startswith("02-Cover-Letter"):  # the exporter renders only the body after the first ---
        parts = re.split(r"^---\s*$", raw, maxsplit=1, flags=re.M)
        return parts[1] if len(parts) == 2 else raw
    return raw


def denoise(text: str) -> str:
    for rx in NOISE:
        text = rx.sub(" ", text)
    return text


def claims(text: str) -> list[tuple[str, str, str]]:
    """(value, unit, context) for every number in `text` after noise removal."""
    out = []
    for m in NUMBER.finditer(text):
        value = m.group(1).replace(",", "")
        unit = WORDNUM.get(m.group(2) or "", m.group(2) or "").lower().replace("×", "x")
        a, b = max(0, m.start() - 50), min(len(text), m.end() + 30)
        ctx = re.sub(r"\s+", " ", text[a:b]).strip()
        out.append((value, unit, ctx))
    return out


def norm(value: str) -> str:
    return value.rstrip("0").rstrip(".") if "." in value else value.lstrip("0") or "0"


def fact_keys(facts_text: str) -> tuple[set[str], set[tuple[str, str]]]:
    values, with_unit = set(), set()
    for value, unit, _ in claims(facts_text):
        values.add(norm(value))
        if unit:
            with_unit.add((norm(value), unit))
    return values, with_unit


def is_trivial(value: str, unit: str) -> bool:
    # 0 and 1 carry no claim on their own ("one page", "1:1"); keep them when a unit gives them meaning
    return not unit and norm(value) in {"0", "1"}


def check(paths: list[Path], facts_texts: list[str]) -> list[dict]:
    values: set[str] = set()
    with_unit: set[tuple[str, str]] = set()
    for t in facts_texts:
        v, w = fact_keys(denoise(t))
        values |= v
        with_unit |= w
    findings = []
    for path in paths:
        text = document_text(path)
        for m in MARKERS.finditer(text):
            line = text.count("\n", 0, m.start()) + 1
            findings.append({"file": str(path), "kind": "marker", "claim": m.group(0), "line": line})
        for value, unit, ctx in claims(denoise(text)):
            if is_trivial(value, unit):
                continue
            v = norm(value)
            ok = (v, unit) in with_unit if unit in {"%", "x"} else v in values
            if not ok:
                findings.append(
                    {"file": str(path), "kind": "untraced", "claim": f"{value}{unit}", "context": ctx}
                )
    return findings


def expand(p: Path) -> list[Path]:
    if p.is_dir():
        return [f for f in (p / "01-Resume.html", p / "02-Cover-Letter.md") if f.exists()]
    return [p]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("paths", nargs="+", type=Path, help="application folders or files to check")
    ap.add_argument("--facts", type=Path, help="root of truth (default: facts.md next to the first path)")
    ap.add_argument(
        "--also", type=Path, action="append", default=[], help="extra trusted source (repeatable)"
    )
    ap.add_argument("--json", action="store_true", help="print findings as JSON")
    ap.add_argument("--warn", action="store_true", help="report but exit 0")
    a = ap.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):  # Windows consoles default to cp1252
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    facts = a.facts or a.paths[0].resolve().parent / "facts.md"  # career/<folder>/ or career/<file>
    if not facts.exists():
        print(f"check-trace: facts file not found: {facts}", file=sys.stderr)
        return 2
    files = [f for p in a.paths for f in expand(p)]
    if not files:
        print("check-trace: nothing to check", file=sys.stderr)
        return 2
    # Only facts.md is trusted by default. 03-Job-Description.md is not a raw JD: /job-match writes the
    # candidate's own evidence into it, so trusting it would launder untraced numbers. Numbers about the
    # employer ("40 million users") are flagged too; confirm them and pass a source with --also.
    sources = [s.read_text(encoding="utf-8") for s in [facts, *a.also]]
    findings = check(files, sources)

    if a.json:
        print(json.dumps(findings, ensure_ascii=False, indent=2))
    else:
        for f in findings:
            if f["kind"] == "marker":
                print(f"MARKER    {f['file']}:{f['line']}  {f['claim']}")
            else:
                print(f"UNTRACED  {f['file']}  {f['claim']:>8}  ...{f['context']}...")
        n_m = sum(f["kind"] == "marker" for f in findings)
        print(f"check-trace: {len(files)} file(s), {n_m} marker(s), {len(findings) - n_m} untraced number(s)")
    return 0 if a.warn or not findings else 1


if __name__ == "__main__":
    sys.exit(main())
