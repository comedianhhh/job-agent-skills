"""Compact node, file safety and gate rules, on the scripted model (ACCEPTANCE-prep-graph.md)."""

from __future__ import annotations

import hashlib
import importlib.util
import inspect
from pathlib import Path

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from test_prep import BRIEF, EMAIL, FACTS, GOOD, JOB, RESEARCH, SCREEN, FakeLLM

from apply_graph import compact, gates
from apply_graph.prep import build_prep_graph
from apply_graph.prep_state import SERDE, Plan, TermLink

ROLE = "2026-09-02-Acme-Backend-Engineer-4471"
CLOSED = "2026-08-01-Closedco-Dev"
HEADER = (
    "| Company | Role | Req | Location | Applied | Status | Next step | Folder |\n"
    "|---|---|---|---|---|---|---|---|\n"
)


def make_career(tmp: Path, closed: bool = False) -> Path:
    tmp.mkdir(parents=True, exist_ok=True)
    (tmp / "facts.md").write_text(FACTS, encoding="utf-8")
    rows = [f"| Acme | Backend Engineer | Ashby 1 | Toronto | 2026-09-02 | SCREEN | chat booked | {ROLE} |"]
    (tmp / ROLE).mkdir()
    (tmp / ROLE / "03-Job-Description.md").write_text(JOB, encoding="utf-8")
    if closed:
        rows.append(f"| Closedco | Dev | — | Toronto | 2026-08-01 | REJECTED | after screen | {CLOSED} |")
        d = tmp / CLOSED
        d.mkdir()
        for name, text in {
            "01-Resume.html": "<li>Built ingestion</li>",
            "03-Job-Description.md": "Closedco JD",
            "Closedco-Dev-Jordan.pdf": "%PDF",
            "Closedco-Dev-Cover-Letter-Jordan.pdf": "%PDF",
            "02-Cover-Letter.md": "letter",
            "INTERVIEW-PREP.md": "prep notes",
            "notes.txt": "unknown",
        }.items():
            (d / name).write_text(text, encoding="utf-8")
    (tmp / "tracker.md").write_text("# Pipeline\n\n" + HEADER + "\n".join(rows) + "\n", encoding="utf-8")
    return tmp


def run(llm, career: Path, out: Path):
    graph = build_prep_graph(llm, checkpointer=InMemorySaver(serde=SERDE))
    config = {"configurable": {"thread_id": "t"}}
    inputs = {"invite_text": EMAIL, "job_text": JOB, "facts_text": FACTS, "research_text": RESEARCH,
              "out_dir": str(out), "career_dir": str(career)}  # fmt: skip
    return graph, config, graph.invoke(inputs, config)


def tree_hash(root: Path) -> dict[str, str]:
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def test_every_node_records_time_and_tokens(tmp_path):
    _, _, result = run(FakeLLM(SCREEN, BRIEF, GOOD), make_career(tmp_path / "c"), tmp_path / "out")
    names = [s["node"] for s in result["spans"]]
    assert names == [
        "read_invite",
        "stage_gate",
        "research",
        "plan",
        "plan_gate",
        "verdict",
        "write_prep",
        "compact",
    ]
    assert all({"ms", "input_tokens", "output_tokens"} <= set(s) for s in result["spans"])


def test_compact_archives_only_ticked_closed_folders(tmp_path):
    career = make_career(tmp_path / "c", closed=True)
    graph, config, result = run(FakeLLM(SCREEN, BRIEF, GOOD), career, tmp_path / "out")
    ask = result["__interrupt__"][0].value
    assert ask["ask"] == "compact" and [x["folder"] for x in ask["candidates"]] == [CLOSED]
    plan = {f["name"]: f["action"] for f in ask["candidates"][0]["files"]}
    assert plan == {
        "01-Resume.html": "keep", "03-Job-Description.md": "keep", "Closedco-Dev-Jordan.pdf": "delete",
        "Closedco-Dev-Cover-Letter-Jordan.pdf": "delete", "02-Cover-Letter.md": "delete",
        "INTERVIEW-PREP.md": "delete", "notes.txt": "unknown",
    }  # fmt: skip
    assert ask["candidates"][0]["interviewed"] is True

    approved = [{"folder": CLOSED, "lesson": "map RAG to memory-service"}]
    result = graph.invoke(Command(resume={"approved": approved}), config)
    assert result["verdict"] == "READY"
    assert not (career / CLOSED).exists()
    kept = sorted(p.name for p in (career / "_archive" / CLOSED).iterdir())
    assert kept == ["01-Resume.html", "03-Job-Description.md", "notes.txt"]
    assert (career / "archive.md").read_text(encoding="utf-8") == (
        "- 2026-08-01 | Closedco | Dev | REJECTED | lesson: map RAG to memory-service\n"
    )
    tracker = (career / "tracker.md").read_text(encoding="utf-8")
    assert f"| _archive/{CLOSED} |" in tracker and "| Closedco |" in tracker
    assert (career / ROLE).is_dir()


def test_compact_with_nothing_ticked_changes_nothing(tmp_path):
    career = make_career(tmp_path / "c", closed=True)
    before = tree_hash(career)
    graph, config, _ = run(FakeLLM(SCREEN, BRIEF, GOOD), career, tmp_path / "out")
    graph.invoke(Command(resume={"approved": []}), config)
    assert tree_hash(career) == before


def test_compact_never_touches_a_folder_that_is_not_closed(tmp_path):
    career = make_career(tmp_path / "c", closed=True)
    assert compact.apply(career, [compact.Approval(folder=ROLE)]) == []
    assert (career / ROLE / "03-Job-Description.md").is_file()


def test_pdf_is_kept_when_it_is_the_only_record_of_what_was_sent():
    assert compact.classify("Sent.pdf", {"Sent.pdf"}).action == "keep"
    assert compact.classify("Sent.pdf", {"Sent.pdf", "01-Resume.html"}).action == "delete"


def test_archived_folder_still_counts_in_the_resume_eval():
    script = Path(__file__).resolve().parents[2] / "scripts" / "career-eval.py"
    spec = importlib.util.spec_from_file_location("career_eval", script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert '"_archive"' in inspect.getsource(mod.eval_blocks)  # walks career/_archive/*/ too


def test_a_run_leaves_role_folder_tracker_and_facts_byte_identical(tmp_path):
    career = make_career(tmp_path / "c")
    before = tree_hash(career)
    run(FakeLLM(SCREEN, BRIEF, GOOD), career, tmp_path / "out")  # output goes outside the career folder
    assert tree_hash(career) == before


def plan_with(quote: str) -> Plan:
    return Plan(
        lead_project="Northwind Logistics",
        lead_reason="r",
        terms=[TermLink(term="t", project="p", fact_quote=quote)],
        questions=[],
        pitch="Hello.",
    )


def test_text_after_todo_is_not_evidence():
    problems = gates.check_plan(plan_with("p95 ingestion latency"), FACTS, [])
    assert problems == ["term 't': quote comes from a TODO (unconfirmed) line: 'p95 ingestion latency'"]


def test_confirmed_part_of_a_line_before_its_todo_still_counts():
    # real case (Field24, 2026-11-20): a confirmed line that ends with a TODO about a detail
    facts = FACTS + "\n- Cost: different models for different tasks. `TODO:` which tasks → which models"
    assert gates.check_plan(plan_with("Cost: different models for different tasks."), facts, []) == []


def test_whole_line_quoted_with_list_marker_and_todo_tail_counts():
    # real case (Field24, 2026-11-20, second run): the model copied the full line, marker and TODO included
    line = "- Cost: different models for different tasks. `TODO:` which tasks → which models"
    assert gates.check_plan(plan_with(line), FACTS + "\n" + line, []) == []


def test_human_answer_quoted_with_list_marker_counts():
    # the plan prompt shows answers as "- <answer>"; the model may copy the dash
    answer = "I isolate the model: no tools, empty temp folder."
    assert gates.check_plan(plan_with(f"- {answer}"), FACTS, [answer]) == []


def test_replan_after_answers_gets_a_fresh_retry_budget(tmp_path):
    from test_prep import GAPPY, NOTHING

    bad = GOOD.model_copy(update={"pitch": "I'm not very familiar with Kafka."})
    answer = "RabbitMQ at Northwind"
    fixed = GOOD.model_copy(
        update={"terms": [*GOOD.terms, TermLink(term="Kafka", project="x", fact_quote=answer)]}
    )
    # first phase uses all 3 tries (bad, bad, gappy); after the answer it may still retry once
    llm = FakeLLM(SCREEN, BRIEF, bad, bad, GAPPY, NOTHING, bad, fixed)
    graph, config, result = run(llm, make_career(tmp_path / "c"), tmp_path / "out")
    result = graph.invoke(Command(resume={"answers": [answer]}), config)
    assert result["verdict"] == "READY", result["reasons"]


FIELD24_POSTING = """Our notes: MCP and Next.js appear in our own match matrix, not in the posting.
## Raw posting
Skills: Node.js, PostgreSQL, TypeScript, React.js, AWS, LLMs
Build our agent harness. Nice to have: computer vision, sandboxed execution environments."""


def test_skills_come_from_the_raw_posting_only():
    skills = gates.jd_skills(FIELD24_POSTING)
    assert "MCP" not in skills and "Next.js" not in skills
    assert {"Node.js", "PostgreSQL", "TypeScript", "AWS", "Computer vision", "Sandboxed execution"} <= set(
        skills
    )


def test_a_skill_the_plan_forgot_is_sent_back():
    plan = plan_with("Hello.").model_copy(
        update={"terms": [TermLink(term="TypeScript / React", project="x", fact_quote=None),
                          TermLink(term="LLM evals", project="x", fact_quote=None)]})  # fmt: skip
    missing = gates.uncovered_skills(plan, FIELD24_POSTING)
    assert "TypeScript" not in missing and "React.js" not in missing and "LLMs" not in missing
    assert "Node.js" in missing and "AWS" in missing
    problems = gates.check_plan(plan, FACTS, [], job_text=FIELD24_POSTING)
    assert any("the posting names these skills" in p and "Node.js" in p for p in problems)


def test_a_long_pitch_is_sent_back():
    long_pitch = plan_with("Hello.").model_copy(
        update={"terms": [], "pitch": "word " * (gates.MAX_PITCH_WORDS + 1)}
    )
    problems = gates.check_plan(long_pitch, FACTS, [])
    assert problems == [
        f"pitch is {gates.MAX_PITCH_WORDS + 1} words; cut it to 170 or fewer (about 60 seconds spoken)"
    ]
