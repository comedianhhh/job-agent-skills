"""Copy the shared fictional career/ workspace into every case that declares a scaffold_script.

Run after editing anything under evals/_fixtures/:  python evals/sync_fixtures.py
Cases keep a committed copy so `claude plugin eval` sees a self-contained case directory.
"""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).parent
SRC = ROOT / "_fixtures" / "career"


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


if __name__ == "__main__":
    main()
