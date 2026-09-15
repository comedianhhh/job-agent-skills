"""tracker.md parsing and surgical write-back."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from tracker_api.tracker import Tracker, TrackerError, business_days_between, clean

from .conftest import TRACKER_MD


def test_parses_positional_columns(career: Path):
    rows = Tracker(career / "tracker.md").rows()
    assert len(rows) == 5
    a = rows[0]
    assert a.company == "Affirm"  # bold stripped
    assert a.role == "Software Engineer II — Card"
    assert a.req == "Greenhouse 7981805003"
    assert a.location == "Remote Canada"
    assert a.applied == "2026-09-12" and a.applied_on == date(2026, 9, 12)
    assert a.status == "APPLIED" and a.status_raw == "`APPLIED`"
    assert a.next_step.startswith("✅ 已投")
    assert a.folder_href == "2026-09-12-Affirm-Software-Engineer-II-7981805003/"
    assert a.folder_text == "2026-09-12-Affirm-…"


def test_row_ids_are_stable_and_unique(career: Path):
    t = Tracker(career / "tracker.md")
    ids = [r.id for r in t.rows()]
    assert len(set(ids)) == 5
    assert ids == [r.id for r in t.rows()]  # deterministic across reads
    assert all(len(i) == 10 for i in ids)


def test_unknown_status_and_missing_folder(career: Path):
    rows = Tracker(career / "tracker.md").rows()
    m = rows[4]
    assert m.status is None and m.status_raw == "`PENDING`"
    assert m.folder_href == "" and m.folder_text == ""
    assert m.applied_on is None
    e = rows[3]
    assert e.applied == "~2026-08-31" and e.applied_on == date(2026, 8, 31)


def test_update_status_touches_only_that_cell(career: Path):
    path = career / "tracker.md"
    t = Tracker(path)
    before = path.read_bytes()
    cohere = t.rows()[1]
    after_row = t.update(cohere.id, status="screen")
    assert after_row.status == "SCREEN" and after_row.status_raw == "`SCREEN`"  # backtick style kept

    after = path.read_bytes()
    assert b"\r\n" in after and b"\n\n" not in after.replace(b"\r\n", b"")  # CRLF preserved
    diff = [(x, y) for x, y in zip(before.split(b"\r\n"), after.split(b"\r\n"), strict=True) if x != y]
    assert len(diff) == 1
    old, new = diff[0]
    assert old.replace(b"`APPLIED`", b"`SCREEN`") == new
    # everything around the table survived byte-for-byte
    assert after.startswith(TRACKER_MD.split("| 公司")[0].encode("utf-8"))
    assert after.endswith(b"- [ ] keep this list untouched\r\n")


def test_update_next_step_and_applied(career: Path):
    t = Tracker(career / "tracker.md")
    clio = t.rows()[2]
    r = t.update(clio.id, next_step="submitted | via Workday", applied="2026-09-16", status="APPLIED")
    assert r.next_step == "submitted \\| via Workday"  # pipes escaped so the table stays a table
    assert r.applied_on == date(2026, 9, 16)
    assert r.status == "APPLIED"
    assert len(t.rows()) == 5


def test_update_rejects_bad_status_and_unknown_row(career: Path):
    t = Tracker(career / "tracker.md")
    row = t.rows()[0]
    with pytest.raises(TrackerError):
        t.update(row.id, status="HIRED")
    with pytest.raises(KeyError):
        t.update("nope", status="APPLIED")


def test_add_appends_after_last_row(career: Path):
    path = career / "tracker.md"
    t = Tracker(path)
    new = t.add(
        company="Shopify", role="Developer", req="Lever abc", location="Remote", next_step="run /job-match"
    )
    rows = t.rows()
    assert len(rows) == 6
    assert rows[-1].id == new.id
    assert rows[-1].status == "DRAFT" and rows[-1].status_raw == "`DRAFT`"
    with path.open(encoding="utf-8", newline="") as f:
        lines = f.read().split("\r\n")
    assert lines[rows[-1].line_no + 1] == ""  # blank line after the table is still there
    assert lines[rows[-1].line_no + 2] == "---"
    with pytest.raises(TrackerError):
        t.add(company="Shopify", role="Developer", req="Lever abc")  # duplicate identity


def test_add_with_folder_makes_link(career: Path):
    t = Tracker(career / "tracker.md")
    r = t.add(company="X", role="Y", folder="2026-09-16-X-Y")
    assert r.folder_href == "2026-09-16-X-Y/"
    assert r.cells[-1] == "[2026-09-16-X-Y](2026-09-16-X-Y/)"


def test_no_table_raises(tmp_path: Path):
    p = tmp_path / "tracker.md"
    p.write_text("# Pipeline\n\nnothing here\n", encoding="utf-8")
    with pytest.raises(TrackerError):
        Tracker(p).rows()


def test_english_template_header_and_lf(tmp_path: Path):
    p = tmp_path / "tracker.md"
    p.write_text(
        "# Pipeline\n\n| Company | Role | Req | Location | Applied | Status | Next step | Folder |\n"
        "|---|---|---|---|---|---|---|---|\n"
        "| Acme | Dev | 1 | Remote | 2026-09-01 | APPLIED | wait | [f](f/) |\n",
        encoding="utf-8",
    )
    t = Tracker(p)
    r = t.rows()[0]
    assert r.status == "APPLIED"
    r2 = t.update(r.id, status="rejected")
    assert r2.status_raw == "REJECTED"  # no backticks in this file → none added
    n = t.add(company="B", role="C")
    assert n.status_raw == "DRAFT"
    assert "\r" not in p.read_text(encoding="utf-8")


def test_clean():
    assert clean("**Affirm**") == "Affirm"
    assert clean("[text](href)") == "text"
    assert clean("Ashby `732c05f5…`") == "Ashby 732c05f5…"


def test_business_days_between():
    fri = date(2026, 9, 11)
    assert business_days_between(fri, fri) == 0
    assert business_days_between(fri, date(2026, 9, 14)) == 1  # Mon
    assert business_days_between(fri, date(2026, 9, 25)) == 10  # two weeks later, Fri
    assert business_days_between(fri, date(2026, 9, 1)) == 0
