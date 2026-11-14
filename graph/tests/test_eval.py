"""Telemetry spans and the code-only eval checks, on the scripted model. No network."""

from __future__ import annotations

from types import SimpleNamespace

from test_graph import ACME, APPLY, CLEAN, FACTS, ROLE, SKIP, UNTRACED, FakeLLM

from apply_graph.evalrun import expected_decisions, grade, missing_quotes, run_case, scoreboard
from apply_graph.telemetry import per_node


class UsageLLM(FakeLLM):
    """FakeLLM that reports usage the way the real backends do."""

    def parse(self, system, user, schema):
        out = super().parse(system, user, schema)
        self.last_usage = {"input_tokens": len(user), "output_tokens": 10, "cost_usd": 0.01}
        return out


def test_every_node_gets_a_span_with_time_and_tokens(tmp_path):
    t = run_case(
        "acme", ROLE / "03-Job-Description.md", FACTS, tmp_path, UsageLLM(APPLY, ACME, UNTRACED, CLEAN)
    )
    assert t["end"] == "gate" and t["error"] is None
    nodes = [s["node"] for s in t["spans"]]
    assert nodes == ["match", "research_company", "draft", "trace_check", "draft", "trace_check", "approve"]
    assert all(
        s["calls"] == 1 and s["output_tokens"] == 10 for s in t["spans"] if s["node"] in {"match", "draft"}
    )
    assert all(s["calls"] == 0 for s in t["spans"] if s["node"] == "trace_check")
    assert t["findings_per_draft"][0] > 0 and t["findings_per_draft"][1] == 0
    rows = {r["node"]: r for r in per_node(t["spans"])}
    assert rows["draft"]["runs"] == 2 and rows["draft"]["calls"] == 2
    assert not (ROLE / "02-Cover-Letter.md").exists()  # letters go to the eval folder only


def test_grade_flags_retry_and_passes_clean_quotes(tmp_path):
    t = run_case(
        "acme", ROLE / "03-Job-Description.md", FACTS, tmp_path, UsageLLM(APPLY, ACME, UNTRACED, CLEAN)
    )
    g = grade(t, FACTS, "APPLY")
    assert g["ran"]["ok"] and g["decision"]["ok"] and g["gate"]["ok"]
    assert g["first_draft"]["ok"] is False  # needed a retry
    assert g["paragraphs"]["ok"] is False  # one-line fake letter


def test_skip_run_has_no_draft_checks(tmp_path):
    t = run_case("acme", ROLE / "03-Job-Description.md", FACTS, tmp_path, UsageLLM(SKIP))
    g = grade(t, FACTS, "APPLY")
    assert g["decision"]["ok"] is False
    assert g["first_draft"]["ok"] is None and g["gate"]["ok"] is None


def test_crash_is_graded_not_raised(tmp_path):
    t = run_case(
        "acme", ROLE / "03-Job-Description.md", FACTS, tmp_path, UsageLLM()
    )  # empty script -> IndexError
    assert t["end"] == "error"
    assert grade(t, FACTS, None)["ran"]["ok"] is False


def test_missing_quotes():
    facts = "Stack: C# / .NET 8, ASP.NET Core\nBuilt the **ingestion** pipeline for orders."
    assert missing_quotes(["Stack: C# / .NET 8, ASP.NET Core", "built the ingestion pipeline"], facts) == []
    assert missing_quotes(["Stack: C# ... ASP.NET Core"], facts) == []
    assert missing_quotes(["Led a team of 12 engineers"], facts) == ["Led a team of 12 engineers"]


def test_expected_decisions_reads_tracker():
    tracker = (
        "| Company | Role | Req | Location | Applied | Status | Next step | Folder |\n"
        "|---|---|---|---|---|---|---|---|\n"
        "| A | x | r | l | 2026-11-01 | APPLIED | y | 2026-11-01-A-Role |\n"
        "| B | x | r | l | — | BLOCKED | y | 2026-11-02-B-Role |\n"
        "| C | x | r | l | — | DRAFT | y | 2026-11-03-C-Role |\n"
        "| D | x | r | l | — | APPLIED | y | SCAN-notes.md |\n"
    )
    assert expected_decisions(tracker) == {"2026-11-01-A-Role": "APPLY", "2026-11-02-B-Role": "SKIP"}


def test_scoreboard_diffs_against_previous(tmp_path):
    args = SimpleNamespace(backend="claude-code", model=None, effort="medium", note="tighter draft prompt")
    t = run_case(
        "acme", ROLE / "03-Job-Description.md", FACTS, tmp_path, UsageLLM(APPLY, ACME, UNTRACED, CLEAN)
    )
    g = grade(t, FACTS, "APPLY")
    _, before = scoreboard("v1", "score", [t], {"acme": g}, args, None)
    fixed = {k: dict(v) for k, v in g.items()} | {"first_draft": {"ok": True, "why": ""}}
    md, after = scoreboard("v2", "score", [t], {"acme": fixed}, args, before)
    assert "fixed: acme · first_draft" in md and "tighter draft prompt" in md
    assert after["score"] > before["score"]
    assert "| draft | 2 | 2 |" in md


def test_joined_quotes_and_short_notes_pass_but_commentary_fails():
    facts = "Attigas Studio — Toronto, ON | 09/2024 – 04/2025\n21-case eval suite with 110 graders [PT]\n"
    ok = "Attigas Studio — Toronto, ON | 09/2024 – 04/2025 (8 months); x — 21-case"
    ok += " eval suite with 110 graders"
    bad = "21-case eval suite with 110 graders. Partial: the facts record no production evals"
    assert missing_quotes([ok], facts) == []
    assert missing_quotes([bad], facts) == [bad]
