"""Tests for career-eval.py. Run: python scripts/test_career_eval.py  (or pytest scripts/)."""

from __future__ import annotations

import importlib.util
import tempfile
from datetime import date
from pathlib import Path

_spec = importlib.util.spec_from_file_location("career_eval", Path(__file__).with_name("career-eval.py"))
ce = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ce)

BLOCKS = """# Blocks

## Northwind | 2024 – 2025
- **NW-1** Owned the shipment-events ingestion service end to end with PostgreSQL and RabbitMQ, carrier webhooks into an idempotent event log.
- **NW-2** Replaced cron polling with webhook ingestion and an event log, cutting carrier update latency from fifteen minutes to thirty seconds.
- **NW-3** Built the integration suite with xUnit and Testcontainers running on every pull request in GitHub Actions for the ingestion service.

## Unity work | 2023
- Built Unity editor tooling that resolves ARKit blendshape channels and joint hierarchies exported from Maya for character rigs.
- Skills: C#, Python, PostgreSQL, RabbitMQ, Unity, Maya, GitHub Actions, Testcontainers, FastAPI, Docker.

## Variants
- 改写版（20 词）：`Replaced cron polling with webhook ingestion and an event log, cutting carrier update latency to thirty seconds.`
"""

JD = """# Backend Engineer — Acme

| Requirement | Weight | Evidence | Status |
|---|---|---|---|
| Event ingestion with webhooks and PostgreSQL | high | NW-1 Unity blendshape | MATCHED |
| CI with integration tests | med | NW-3 | MATCHED |
"""

RESUME = """<html><body><ul>
<li>Owned the shipment-events ingestion service end to end with <b>PostgreSQL</b> and RabbitMQ, carrier webhooks into an idempotent event log.</li>
<li>Replaced cron polling with webhook ingestion and an event log, cutting carrier update latency to thirty seconds.</li>
<li>Wrote a brand new sentence that is not in any block at all, about something else entirely.</li>
</ul></body></html>"""

TRACKER = """# Pipeline

| Company | Role | Req | Location | Applied | Status | Next step | Folder |
|---|---|---|---|---|---|---|---|
| Acme | Backend Engineer | — | Remote | 2026-09-01 | SCREEN | prep | 2026-09-01-Acme |
| Beta | Senior AI Engineer, Agents | — | Remote | 2026-09-01 | APPLIED | follow up | — |
| Gamma | Gameplay Programmer | — | Remote | 2026-10-08 | APPLIED | wait | — |
| Delta | Backend Engineer | — | Remote | 2026-09-02 | DRAFT | — | — |

## Outreach

| Company / Team | Contact Person | Role & Context | Date | Channel | Status | Next Step |
|---|---|---|---|---|---|---|
| Acme | Pat | Recruiter | 2026-09-01 | LinkedIn | SENT | wait |

## Archived

| Company | Role | Req | Location | Batch Date | Original Status | Archived Status | Note |
|---|---|---|---|---|---|---|---|
| Echo | AI Engineer | — | Remote | ~2026-08-31 | SCREEN | EXPIRED | expired |
| Foxtrot | Software Engineer | — | Remote | 2026-09-04 | APPLIED | GHOSTED | none |
"""


def _career(tmp: Path) -> Path:
    (tmp / "blocks.md").write_text(BLOCKS, encoding="utf-8")
    (tmp / "tracker.md").write_text(TRACKER, encoding="utf-8")
    d = tmp / "2026-09-01-Acme"
    d.mkdir()
    (d / "01-Resume.html").write_text(RESUME, encoding="utf-8")
    (d / "03-Job-Description.md").write_text(JD, encoding="utf-8")
    (tmp / "application").mkdir()  # the template folder is never evaluated
    return tmp


def test_parse_blocks_ids_notes_and_variants():
    blocks = ce.parse_blocks(BLOCKS)
    ids = [b["id"] for b in blocks]
    assert ids[:3] == ["NW-1", "NW-2", "NW-3"]
    assert "Unity-1" in ids
    assert not any(b["text"].startswith("Skills") for b in blocks)  # assembly notes dropped
    variant = next(b for b in blocks if b["id"].startswith("Variants"))
    assert variant["text"].startswith("Replaced cron polling")  # quoted bullet extracted
    assert variant["cluster"] == "NW-2"  # merged with its original


def test_jd_query_never_includes_evidence_column():
    q = ce.jd_query(JD)
    assert "webhooks" in q and "integration tests" in q
    assert "blendshape" not in q and "NW-1" not in q


def test_jd_query_prefers_raw_posting():
    q = ce.jd_query(
        "# T\n\n## Raw posting\nWe need Go.\n\n## Requirement–evidence matrix\n| Requirement |\n|---|\n| Rust |\n"
    )
    assert "Go" in q and "Rust" not in q


def test_eval_blocks_labels_assembly_and_recall():
    with tempfile.TemporaryDirectory() as t:
        r = ce.eval_blocks(_career(Path(t)))
    assert r["summary"]["folders"] == 1
    row = r["rows"][0]
    assert row["bullets"] == 3 and row["assembled"] == 2
    assert row["labels"] == ["NW-1", "NW-2"]
    assert row["recall@10"] == 1.0  # tiny index: everything is in the top 10
    assert 0 <= row["r_precision"] <= 1


def test_outcomes_counts_windows_archives_and_ci():
    with tempfile.TemporaryDirectory() as t:
        r = ce.eval_outcomes(_career(Path(t)), today=date(2026, 10, 9))
    # decided: Acme SCREEN, Beta (past window), Echo (reached SCREEN before expiring), Foxtrot GHOSTED
    assert r["decided"] == 4 and r["pending"] == 1 and r["excluded"] == 1
    assert r["overall"]["interviews"] == 2
    assert r["by_track"]["ai"]["n"] == 2 and r["by_track"]["ai"]["interviews"] == 1
    assert r["by_seniority"]["senior+"]["n"] == 1
    assert r["by_tailored"]["unknown (archived)"]["n"] == 2
    lo, hi = r["overall"]["ci95"]
    assert lo < 0.5 < hi


def test_source_and_stretch_read_the_trackers_own_words():
    app = {"company": "Coalition", "req": "Greenhouse 4731294005 (LinkedIn 4463625729)", "notes": ""}
    assert ce.source(app) == "greenhouse"
    assert ce.source({"company": "X", "req": "LinkedIn Easy Apply 123", "notes": ""}) == "linkedin easy apply"
    assert ce.source({"company": "STRATIS (via Vladimir, Head of Eng)", "req": "—", "notes": ""}) == "direct contact"
    assert ce.source({"company": "X", "req": "—", "notes": "applied via Indeed"}) == "indeed"
    assert ce.source({"company": "X", "req": "—", "notes": ""}) == "unknown"
    assert ce.stretch({"notes": "Stretch: 5+ yrs asked vs 4"}).startswith("stretch")
    assert ce.stretch({"notes": "posting asks 7+ yrs"}).startswith("stretch")
    assert ce.stretch({"notes": "Follow up on LinkedIn 2026-11-23"}) == "within range"


def _synthetic(groups: dict[str, tuple[int, int]]) -> dict:
    """An eval_outcomes-shaped result with one dimension (by_source) filled in."""
    k = sum(a for a, _ in groups.values())
    n = sum(b for _, b in groups.values())
    empty = {key: {} for _, key in ce.GROUPS}
    by_source = {
        g: {"interviews": a, "n": b, "rate": a / b, "ci95": ce.wilson(a, b)} for g, (a, b) in groups.items()
    }
    return {
        **empty,
        "overall": {"interviews": k, "n": n, "rate": k / n, "ci95": ce.wilson(k, n)},
        "by_source": by_source,
        "pending": 0,
        "decided": n,
        "excluded": 0,
        "interviews": [],
    }


def test_signals_need_size_and_separation():
    strong = ce.signals(_synthetic({"referral": (6, 8), "job board": (2, 60)}))
    assert [(s["group"], s["strength"]) for s in strong][0] == ("referral", "strong")
    weak = ce.signals(_synthetic({"greenhouse": (2, 10), "indeed": (1, 30)}))
    assert ("greenhouse", "weak") in [(s["group"], s["strength"]) for s in weak]
    assert ce.signals(_synthetic({"ashby": (1, 3), "indeed": (2, 60)})) == []  # n < 5: noise
    assert ce.signals(_synthetic({"a": (1, 20), "b": (1, 20)})) == []  # no gap


def test_calibrate_writes_markdown_and_says_when_there_is_no_signal():
    with tempfile.TemporaryDirectory() as t:
        career = _career(Path(t))
        assert ce.main(["calibrate", str(career)]) == 0
        md = (career / "calibration.md").read_text(encoding="utf-8")
    assert md.startswith("# Calibration from past applications")
    assert "None yet" in md  # four decided applications cannot carry a signal
    assert "- Acme — Backend Engineer" in md
    assert "| Source |" in md and "| Stretch |" in md


def test_wilson_edges():
    assert ce.wilson(0, 0) == (0.0, 0.0)
    lo, hi = ce.wilson(0, 10)
    assert lo == 0.0 and 0.2 < hi < 0.35


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
