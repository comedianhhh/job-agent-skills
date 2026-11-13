"""Copy the shared fictional career/ workspace into every case that declares a scaffold_script.

Run after editing anything under evals/_fixtures/:  python evals/sync_fixtures.py
Cases keep a committed copy so `claude plugin eval` sees a self-contained case directory.
It also refreshes the verbatim source blocks in llm graders (see SOURCES_RE below).
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

ROOT = Path(__file__).parent
SRC = ROOT / "_fixtures" / "career"

# An llm judge sees only its rubric and the reply, never the workspace. A rubric that judges
# "invented facts" must therefore carry the source files themselves, verbatim: hand-written
# summaries drop details, and a correct reply that quotes a dropped detail then fails.
# A grader asks for files with a marker block; this script fills it, and validate.py fails
# when a block no longer matches the fixture.
#   <!-- fixture-sources: facts.md blocks.md 2026-09-02-Acme-Backend-Engineer-4471/03-Job-Description.md -->
#   <!-- /fixture-sources -->
SOURCES_RE = re.compile(r"(<!-- fixture-sources: ([^>]*?) -->)\n.*?(<!-- /fixture-sources -->)", re.S)


def render_sources(names: str) -> str:
    parts = []
    for name in names.split():
        text = (SRC / name).read_text(encoding="utf-8").strip()
        parts.append(f"**career/{name}**, verbatim:\n\n````markdown\n{text}\n````\n")
    return "\n".join(parts)


def render_grader(text: str) -> str:
    return SOURCES_RE.sub(lambda m: f"{m.group(1)}\n{render_sources(m.group(2))}{m.group(3)}", text)


def grader_files() -> list[Path]:
    return [p for p in ROOT.rglob("graders/*.md") if "results" not in p.parts and "fixture-sources:" in p.read_text(encoding="utf-8")]


def sync_grader_sources() -> int:
    n = 0
    for g in grader_files():
        old = g.read_text(encoding="utf-8")
        new = render_grader(old)
        if new != old:
            g.write_text(new, encoding="utf-8", newline="\n")
        n += 1
    return n


def main() -> None:
    n = 0
    for case_yaml in ROOT.rglob("case.yaml"):
        if "_fixtures" in case_yaml.parts or "results" in case_yaml.parts:
            continue
        text = case_yaml.read_text(encoding="utf-8")
        if "scaffold_script" not in text:
            continue
        dst = case_yaml.parent / "resources" / "career"
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(SRC, dst)
        n += 1
    print(f"synced career/ fixture into {n} case(s)")
    print(f"refreshed fixture sources in {sync_grader_sources()} llm grader(s)")


if __name__ == "__main__":
    main()
