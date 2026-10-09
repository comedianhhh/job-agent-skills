"""Tests for check-trace.py. Run: python scripts/test_check_trace.py  (or pytest scripts/)."""

from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path

_spec = importlib.util.spec_from_file_location("check_trace", Path(__file__).with_name("check-trace.py"))
ct = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ct)

FACTS = """
## Basics
- Contact & links -> answers.yaml
## SoulLink | 05/2025 – 09/2026
- Cut rig setup 75% with editor tooling; 52 ARKit channels.
- Product Hunt #3 of the day, 256 upvotes; App Store 4.5★ from 74 ratings.
- Load time 3x faster after async streaming.
"""


def _app(tmp: Path, resume_body: str, letter_body: str = "Thanks.") -> Path:
    (tmp / "facts.md").write_text(FACTS, encoding="utf-8")
    d = tmp / "2026-10-01-Acme-Engineer"
    d.mkdir()
    (d / "01-Resume.html").write_text(
        "<html><head><title>x 999</title></head><body>"
        '<header id="title"><h1>Name</h1><span>+1 (437) 555-0100 · a@b.com · M4S 0B1</span></header>'
        f"<ul><li>{resume_body}</li></ul><p>May 2022 – Sep 2026 · 2019 – 2023 · React 19/18 · Unity 6</p>"
        "</body></html>",
        encoding="utf-8",
    )
    (d / "02-Cover-Letter.md").write_text(
        f"Name\n+1 437 555 0100\n\n---\n\n{letter_body}\n", encoding="utf-8"
    )
    return d


def run(resume_body: str, letter_body: str = "Thanks.") -> list[dict]:
    with tempfile.TemporaryDirectory() as t:
        d = _app(Path(t), resume_body, letter_body)
        return ct.check(ct.expand(d), [(Path(t) / "facts.md").read_text(encoding="utf-8")])


def test_traced_numbers_pass_and_noise_is_ignored():
    assert run("Cut rig setup <b>75%</b>; 52 channels; 256 upvotes; 4.5★; 3× faster.") == []


def test_invented_number_is_caught_with_context():
    f = run("Cut rig setup 80% with tooling.")
    assert [(x["kind"], x["claim"]) for x in f] == [("untraced", "80%")]
    assert "rig setup" in f[0]["context"]


def test_unit_matters_for_percent_and_multiplier():
    # 74 exists as a count ("74 ratings"), not as a percentage or a multiplier
    assert [x["claim"] for x in run("Improved retention 74%.")] == ["74%"]
    assert [x["claim"] for x in run("Load time 75x faster.")] == ["75x"]
    assert run("Rated by 74 users.") == []


def test_heading_numbers_and_scientific_notation_are_noise():
    with tempfile.TemporaryDirectory() as t:
        doc = Path(t) / "notes.md"
        doc.write_text("## 13. Research\n### 3.2 Details\nResolution about 2×10⁻¹⁰ per step.\n", encoding="utf-8")
        assert ct.check([doc], [FACTS]) == []


def test_markers_fail():
    f = run("Led [TBD] engineers.", "TODO: add metric")
    assert {x["claim"] for x in f if x["kind"] == "marker"} == {"[TBD]", "TODO"}


def test_cover_letter_header_is_not_checked():
    assert run("52 channels.", "Body with 256 upvotes.") == []


def test_jd_analysis_is_not_trusted_by_default():
    # 03-Job-Description.md holds /job-match's evidence column; trusting it would launder numbers
    with tempfile.TemporaryDirectory() as t:
        d = _app(Path(t), "Cut setup 90%.")
        (d / "03-Job-Description.md").write_text("| evidence | setup −90% |", encoding="utf-8")
        assert ct.main([str(d)]) == 1
        assert ct.main([str(d), "--also", str(d / "03-Job-Description.md")]) == 0


def test_main_exit_codes():
    with tempfile.TemporaryDirectory() as t:
        d = _app(Path(t), "Saved 99% of time.")
        assert ct.main([str(d)]) == 1
        assert ct.main([str(d), "--warn"]) == 0
        assert ct.main([str(Path(t) / "missing"), "--facts", str(Path(t) / "nope.md")]) == 2


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
