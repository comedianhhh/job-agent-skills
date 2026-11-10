#!/usr/bin/env python3
"""Which resume line to cut first when the page overflows — by relevance, not by age.

    python scripts/rank-cuts.py career/2026-11-09-Acme-Backend/          # table, lowest score first
    python scripts/rank-cuts.py career/<folder>/ --json

The usual fix for a two-page resume is to trim the oldest role. That throws away an old bullet that
hits the posting and keeps a recent one that does not. Each bullet in 01-Resume.html gets three
scores, all in [0, 1]:

  relevance   BM25 against the posting (## Raw posting of 03-Job-Description.md, else its
              requirement column), normalised to the best bullet           weight 0.60
  uniqueness  1 − the highest word overlap (Jaccard) with any other bullet;
              a bullet that repeats another's proof is cheap to lose         weight 0.25
  letter      share of the bullet's words that 02-Cover-Letter.md reuses;
              cutting a line the letter leans on breaks the pair             weight 0.15

Cut from the top of the table. It ranks; the model and the user still decide (a low-relevance
line can be the only proof of a hard requirement — check the requirement–evidence matrix).

Exit status: 0, or 2 on usage error. Stdlib only; reuses BM25 from jobs-mcp and parsing from
career-eval.py.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("career_eval", HERE / "career-eval.py")
ce = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ce)

WEIGHTS = {"relevance": 0.60, "uniqueness": 0.25, "letter": 0.15}


def letter_body(md: str) -> str:
    parts = re.split(r"^---\s*$", md, maxsplit=1, flags=re.M)
    return parts[1] if len(parts) == 2 else md


def rank(bullets: list[str], jd: str, letter: str = "") -> list[dict]:
    if not bullets:
        return []
    rel = ce.bm25(jd, bullets)
    top = max(rel) or 1.0
    toks = [set(ce.tokenize(b)) for b in bullets]
    letter_toks = set(ce.tokenize(letter))
    rows = []
    for i, b in enumerate(bullets):
        others = [len(toks[i] & toks[j]) / len(toks[i] | toks[j]) for j in range(len(bullets)) if j != i and toks[j]]
        scores = {
            "relevance": rel[i] / top,
            "uniqueness": 1 - max(others, default=0.0),
            "letter": len(toks[i] & letter_toks) / len(toks[i]) if toks[i] and letter_toks else 0.0,
        }
        rows.append(
            {
                "bullet": b,
                **{k: round(v, 3) for k, v in scores.items()},
                "score": round(sum(WEIGHTS[k] * v for k, v in scores.items()), 3),
            }
        )
    return sorted(rows, key=lambda r: r["score"])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("folder", type=Path, help="application folder with 01-Resume.html and 03-Job-Description.md")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    resume, jd = a.folder / "01-Resume.html", a.folder / "03-Job-Description.md"
    if not resume.exists() or not jd.exists():
        print(f"rank-cuts: need {resume} and {jd}", file=sys.stderr)
        return 2
    letter = a.folder / "02-Cover-Letter.md"
    md = jd.read_text(encoding="utf-8")
    query = ce.jd_query(md)
    if len(ce.tokenize(query)) < 30:  # a short hand-written summary: no raw posting, no matrix
        query = md
    rows = rank(
        ce.resume_bullets(resume.read_text(encoding="utf-8")),
        query,
        letter_body(letter.read_text(encoding="utf-8")) if letter.exists() else "",
    )
    if a.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    print("| # | Score | Relevance | Unique | Letter | Bullet |")
    print("|---|---|---|---|---|---|")
    for i, r in enumerate(rows, 1):
        text = r["bullet"][:80] + ("…" if len(r["bullet"]) > 80 else "")
        print(f"| {i} | {r['score']:.2f} | {r['relevance']:.2f} | {r['uniqueness']:.2f} | {r['letter']:.2f} | {text} |")
    print(f"\nrank-cuts: {len(rows)} bullet(s); cut from #1 down, re-export after each cut.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
