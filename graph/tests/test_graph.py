"""Every path through the graph, on a scripted model. No network, no API key."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from apply_graph import MAX_DRAFTS, build_graph
from apply_graph.state import SERDE, CompanyBrief, CoverLetter, Match, Requirement

FIXTURES = Path(__file__).resolve().parents[2] / "evals" / "_fixtures" / "career"
FACTS = (FIXTURES / "facts.md").read_text(encoding="utf-8")
ROLE = FIXTURES / "2026-09-02-Acme-Backend-Engineer-4471"
JOB = (ROLE / "03-Job-Description.md").read_text(encoding="utf-8")

APPLY = Match(
    decision="APPLY",
    reason="Backend C# role in Toronto; event-driven ingestion matches.",
    requirements=[
        Requirement(requirement="C# / .NET", evidence="Stack: C# / .NET 8, ASP.NET Core"),
        Requirement(requirement="Kafka", evidence=None),
    ],
)
ACME = CompanyBrief(product="Logistics tracking platform", team_focus="Event ingestion", values=["testing"])
SKIP = Match(decision="SKIP", reason="US work authorization required.", requirements=[])
# 15 minutes / 30 seconds / 140 tests are all in the fixture facts.md
CLEAN = CoverLetter(body="I cut update latency from ~15 minutes to under 30 seconds and wrote 140 tests.")
UNTRACED = CoverLetter(body="I improved ingestion throughput by 80% across 12 services.")


class FakeLLM:
    def __init__(self, *outputs):
        self.outputs = list(outputs)
        self.calls: list[tuple[str, str]] = []

    def parse(self, system, user, schema):
        self.calls.append((schema.__name__, user))
        out = self.outputs.pop(0)
        assert isinstance(out, schema), f"graph asked for {schema.__name__}, script has {type(out).__name__}"
        return out


def start(llm, tmp_path, checkpointer=None, thread="t1"):
    graph = build_graph(llm, checkpointer=checkpointer or InMemorySaver(serde=SERDE))
    config = {"configurable": {"thread_id": thread}}
    result = graph.invoke({"job_text": JOB, "facts_text": FACTS, "out_dir": str(tmp_path)}, config)
    return graph, config, result


def test_clean_draft_stops_for_approval_then_records_ready(tmp_path):
    llm = FakeLLM(APPLY, ACME, CLEAN)
    graph, config, result = start(llm, tmp_path)

    assert "__interrupt__" in result
    assert result["__interrupt__"][0].value["draft"] == CLEAN.body
    assert "Logistics tracking platform" in llm.calls[2][1]  # the brief reaches the draft prompt
    assert not (tmp_path / "README.md").exists()  # nothing recorded before a human says yes

    result = graph.invoke(Command(resume={"approved": True}), config)
    assert result["status"] == "READY"
    readme = (tmp_path / "README.md").read_text(encoding="utf-8")
    assert "Status: READY" in readme and "| Kafka | **gap** |" in readme


def test_untraced_number_is_sent_back_with_the_claims(tmp_path):
    llm = FakeLLM(APPLY, ACME, UNTRACED, CLEAN)
    _, _, result = start(llm, tmp_path)

    assert "__interrupt__" in result
    assert [c[0] for c in llm.calls] == ["Match", "CompanyBrief", "CoverLetter", "CoverLetter"]
    redraft_prompt = llm.calls[3][1]
    assert "80%" in redraft_prompt and "12" in redraft_prompt


def test_gives_up_after_max_drafts_without_asking_a_human(tmp_path):
    llm = FakeLLM(APPLY, ACME, *[UNTRACED] * MAX_DRAFTS)
    _, _, result = start(llm, tmp_path)

    assert "__interrupt__" not in result
    assert result["status"] == "BLOCKED" and result["attempts"] == MAX_DRAFTS
    assert not llm.outputs


def test_skip_never_drafts(tmp_path):
    llm = FakeLLM(SKIP)
    _, _, result = start(llm, tmp_path)

    assert result["status"] == "SKIPPED"
    assert [c[0] for c in llm.calls] == ["Match"]
    assert not (tmp_path / "02-Cover-Letter.md").exists()


def test_human_note_goes_into_the_redraft(tmp_path):
    llm = FakeLLM(APPLY, ACME, CLEAN, CLEAN)
    graph, config, _ = start(llm, tmp_path)

    result = graph.invoke(Command(resume={"approved": False, "note": "lead with the test suite"}), config)
    assert "__interrupt__" in result
    assert "lead with the test suite" in llm.calls[-1][1]

    result = graph.invoke(Command(resume={"approved": False, "note": ""}), config)
    assert result["status"] == "REJECTED"


def test_resume_from_sqlite_in_a_new_graph(tmp_path):
    db = tmp_path / ".graph.sqlite"
    conn = sqlite3.connect(db, check_same_thread=False)
    start(FakeLLM(APPLY, ACME, CLEAN), tmp_path, checkpointer=SqliteSaver(conn, serde=SERDE), thread="acme")
    conn.close()

    # a later process: fresh connection, fresh graph, a model that must not be called again
    conn = sqlite3.connect(db, check_same_thread=False)
    graph = build_graph(FakeLLM(), checkpointer=SqliteSaver(conn, serde=SERDE))
    config = {"configurable": {"thread_id": "acme"}}
    snapshot = graph.get_state(config)
    assert snapshot.next == ("approve",)

    result = graph.invoke(Command(resume={"approved": True}), config)
    assert result["status"] == "READY"
    assert result["log"][0].startswith("match: APPLY")
    conn.close()


@pytest.mark.parametrize("draft", [CLEAN.body, "TODO: add a metric"])
def test_trace_gate_matches_the_cli_script(tmp_path, draft):
    from apply_graph import trace

    letter = tmp_path / "02-Cover-Letter.md"
    letter.write_text(f"---\n---\n{draft}\n", encoding="utf-8")
    assert bool(trace.check(letter, FACTS)) == draft.startswith("TODO")


def test_claude_code_backend_reads_structured_output(monkeypatch):
    import json
    import subprocess

    from apply_graph.llm import ClaudeCodeLLM

    seen = {}

    def fake_run(cmd, input, **kw):
        seen["cmd"], seen["input"] = cmd, input
        out = {"is_error": False, "structured_output": SKIP.model_dump()}
        return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps(out), stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert ClaudeCodeLLM(exe="claude").parse("sys", "the posting", Match) == SKIP
    assert seen["input"] == "the posting"
    assert seen["cmd"][seen["cmd"].index("--tools") + 1] == ""  # no file or shell access
