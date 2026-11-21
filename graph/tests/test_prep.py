"""Every path through the interview-prep graph, on a scripted model. No network."""

from __future__ import annotations

from pathlib import Path

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from apply_graph import gates
from apply_graph.prep import MAX_PLANS, build_prep_graph
from apply_graph.prep_state import (
    SERDE,
    Brief,
    Claim,
    Evidence,
    EvidenceList,
    Invite,
    Plan,
    Question,
    TermLink,
)

FIXTURES = Path(__file__).resolve().parents[2] / "evals" / "_fixtures" / "career"
FACTS = (FIXTURES / "facts.md").read_text(encoding="utf-8")
JOB = (FIXTURES / "2026-09-02-Acme-Backend-Engineer-4471" / "03-Job-Description.md").read_text(
    encoding="utf-8"
)

EMAIL = "Hi Jordan, we are moving you to the next stage! It'll be a 30min chat with our CTO. Book here."
RESEARCH = "Acme tracks freight in real time. New this month: carrier webhooks for every shipment."
SCREEN = Invite(stage="SCREEN", evidence="we are moving you to the next stage!", interviewer="CTO")
REJECT = Invite(stage="REJECTED", evidence="Hi Jordan,")
MADE_UP = Invite(stage="SCREEN", evidence="We loved your interview and want to move fast.")
BRIEF = Brief(
    product=[Claim(text="Real-time freight tracking", quote="Acme tracks freight in real time.")],
    current_bet=[Claim(text="Carrier webhooks", quote="carrier webhooks for every shipment")],
    interviewer=[Claim(text="Ex-Google CTO", quote="former Google engineer")],  # not in research: dropped
)
INGEST = "Owned the shipment-events ingestion service end to end"
GOOD = Plan(
    lead_project="Northwind Logistics",
    lead_reason="They ship carrier webhooks; Jordan built exactly that ingestion.",
    terms=[
        TermLink(term="event ingestion", project="Northwind Logistics", fact_quote=INGEST),
        # every skill the fixture posting names has a term (the coverage gate checks this)
        TermLink(
            term="C#, Java or Python", project="Northwind Logistics", fact_quote="C# / .NET 8, ASP.NET Core"
        ),
        TermLink(
            term="PostgreSQL", project="Northwind Logistics", fact_quote="append-only event log in PostgreSQL"
        ),
        TermLink(
            term="Kafka-style event pipeline",
            project="Northwind Logistics",
            fact_quote="consumes carrier webhooks",
        ),
        TermLink(term="Kubernetes", project="none in production", fact_quote="No Kubernetes in production"),
    ],
    questions=[
        Question(
            question="Walk me through the ingestion service",
            intent="ownership",
            must_cover=["design", "latency"],
            fact_quote=INGEST,
        )
    ],
    pitch="So I cut update latency from about 15 minutes to under 30 seconds, and wrote 140 tests.",
)
GAPPY = GOOD.model_copy(
    update={"terms": [*GOOD.terms, TermLink(term="Kafka", project=None, fact_quote=None)]}
)
NOTHING = EvidenceList(items=[])
BAD = GOOD.model_copy(update={"pitch": "I'm not very familiar with Kafka, but I sped things up 80%."})


class FakeLLM:
    def __init__(self, *outputs):
        self.outputs = list(outputs)
        self.calls: list[tuple[str, str]] = []

    def parse(self, system, user, schema):
        self.calls.append((schema.__name__, user))
        out = self.outputs.pop(0)
        assert isinstance(out, schema), f"graph asked for {schema.__name__}, script has {type(out).__name__}"
        return out


def run(llm, tmp_path, email=EMAIL, research=RESEARCH):
    graph = build_prep_graph(llm, checkpointer=InMemorySaver(serde=SERDE))
    config = {"configurable": {"thread_id": "t"}}
    inputs = {
        "invite_text": email,
        "job_text": JOB,
        "facts_text": FACTS,
        "research_text": research,
        "out_dir": str(tmp_path),
    }
    return graph, config, graph.invoke(inputs, config)


def test_clean_run_is_ready_and_writes_prep(tmp_path):
    _, _, result = run(FakeLLM(SCREEN, BRIEF, GOOD), tmp_path)
    assert result["verdict"] == "READY", result["reasons"]
    assert result["dropped"] == ["Ex-Google CTO"]  # its quote is not in the research text
    text = (tmp_path / "04-Interview-Prep.graph.md").read_text(encoding="utf-8")
    assert "Lead with: Northwind Logistics" in text and "Ex-Google" not in text.split("_Dropped")[0]


def test_rejection_stops_without_prep(tmp_path):
    _, _, result = run(FakeLLM(REJECT), tmp_path)
    assert result["verdict"] == "STOPPED"
    assert not (tmp_path / "04-Interview-Prep.graph.md").exists()


def test_stage_not_in_email_asks_the_human(tmp_path):
    graph, config, result = run(FakeLLM(MADE_UP, BRIEF, GOOD), tmp_path)
    assert result["__interrupt__"][0].value["ask"] == "stage"
    result = graph.invoke(Command(resume={"stage": "SCREEN"}), config)
    assert result["verdict"] == "READY"


def test_bad_pitch_is_sent_back_with_the_reasons(tmp_path):
    llm = FakeLLM(SCREEN, BRIEF, BAD, GOOD)
    _, _, result = run(llm, tmp_path)
    assert result["verdict"] == "READY"
    second_plan_prompt = [u for name, u in llm.calls if name == "Plan"][1]
    assert "talks itself down" in second_plan_prompt and "80%" in second_plan_prompt


def test_plan_that_never_passes_ends_not_ready(tmp_path):
    _, _, result = run(FakeLLM(SCREEN, BRIEF, *[BAD] * MAX_PLANS), tmp_path)
    assert result["verdict"] == "NOT_READY"
    assert any("talks itself down" in r for r in result["reasons"])


def test_gap_is_asked_and_answer_feeds_the_next_plan(tmp_path):
    fixed = GAPPY.model_copy(
        update={
            "terms": [
                *GOOD.terms,
                TermLink(
                    term="Kafka", project="Northwind Logistics", fact_quote="RabbitMQ queue for webhooks"
                ),
            ]
        }
    )
    llm = FakeLLM(SCREEN, BRIEF, GAPPY, NOTHING, fixed)
    graph, config, result = run(llm, tmp_path)
    assert result["__interrupt__"][0].value["gaps"] == ["Kafka: which project or job shows this?"]
    result = graph.invoke(Command(resume={"answers": ["RabbitMQ queue for webhooks at Northwind"]}), config)
    assert result["verdict"] == "READY", result["reasons"]
    assert "RabbitMQ queue for webhooks at Northwind" in [u for n, u in llm.calls if n == "Plan"][1]


def test_unanswered_gap_is_not_ready(tmp_path):
    graph, config, _ = run(FakeLLM(SCREEN, BRIEF, GAPPY, NOTHING), tmp_path)
    result = graph.invoke(Command(resume={"answers": []}), config)
    assert result["verdict"] == "NOT_READY"
    text = (tmp_path / "04-Interview-Prep.graph.md").read_text(encoding="utf-8")
    assert "do not say “not familiar”" in text


def test_no_research_is_not_ready(tmp_path):
    _, _, result = run(FakeLLM(SCREEN, GOOD), tmp_path, research="")
    assert result["verdict"] == "NOT_READY"
    assert any("JD only" in r for r in result["reasons"])


def test_quoted_handles_ellipsis_whitespace_and_curly_quotes():
    src = "Owned the shipment-events ingestion   service end to end (design, implementation, on-call)"
    assert gates.quoted("Owned the shipment-events ingestion service ... on-call", src)
    assert not gates.quoted("Owned the payments service", src)
    assert gates.quoted("it’s live", "it's live")


def run_with_sources(llm, tmp_path, sources):
    graph = build_prep_graph(llm, checkpointer=InMemorySaver(serde=SERDE))
    config = {"configurable": {"thread_id": "t"}}
    inputs = {
        "invite_text": EMAIL,
        "job_text": JOB,
        "facts_text": FACTS,
        "research_text": RESEARCH,
        "out_dir": str(tmp_path),
        "sources": sources,
    }
    return graph, config, graph.invoke(inputs, config)


KAFKA_GAP = "Kafka: which project or job shows this?"


def test_gap_covered_by_facts_is_used_without_asking(tmp_path):
    hit = EvidenceList(
        items=[
            Evidence(
                gap=KAFKA_GAP,
                source="facts.md",
                quote="Redis, RabbitMQ",
                answer="I used RabbitMQ, not Kafka.",
                strength="partial",
            )
        ]
    )
    llm = FakeLLM(SCREEN, BRIEF, GAPPY, hit)  # no second plan: code fills the hit in
    _, _, result = run_with_sources(llm, tmp_path, {})
    assert "__interrupt__" not in result and result["verdict"] == "READY", result.get("reasons")
    assert [n for n, _ in llm.calls].count("Plan") == 1
    kafka = next(t for t in result["plan"].terms if t.term == "Kafka")
    assert (kafka.project, kafka.fact_quote) == ("facts.md (partial)", "Redis, RabbitMQ")


def test_found_facts_survive_a_replan_that_drops_them(tmp_path):
    # real case (Field24, 2026-11-20): a later plan forgot the found evidence; code fills it in again
    go = TermLink(term="Go", project=None, fact_quote=None)
    two_gaps = GOOD.model_copy(
        update={"terms": [*GOOD.terms, TermLink(term="Kafka", project=None, fact_quote=None), go]}
    )
    hit = EvidenceList(items=[Evidence(gap=KAFKA_GAP, source="facts.md", quote="Redis, RabbitMQ",
                                       answer="x", strength="partial")])  # fmt: skip
    answered = "I wrote a Go CLI at a hackathon."
    replan = two_gaps.model_copy(  # the model drops Kafka's quote again, uses the new answer for Go
        update={"terms": [*GOOD.terms, TermLink(term="Kafka", project=None, fact_quote=None),
                          TermLink(term="Go", project="hackathon", fact_quote=answered)]})  # fmt: skip
    llm = FakeLLM(SCREEN, BRIEF, two_gaps, hit, replan)
    graph, config, result = run_with_sources(llm, tmp_path, {})
    assert result["__interrupt__"][0].value["gaps"] == ["Go: which project or job shows this?"]
    result = graph.invoke(Command(resume={"answers": [answered]}), config)
    assert result["verdict"] == "READY", result["reasons"]
    kafka = next(t for t in result["plan"].terms if t.term == "Kafka")
    assert kafka.fact_quote == "Redis, RabbitMQ"
    assert "<found>" in [u for n, u in llm.calls if n == "Plan"][1]


def test_gap_found_in_another_file_is_proposed_then_confirmed(tmp_path):
    stories = {"stories.md": "## S9\nRan Kafka at a weekend hackathon for a demo."}
    hit = EvidenceList(
        items=[
            Evidence(
                gap=KAFKA_GAP,
                source="stories.md",
                quote="Ran Kafka at a weekend hackathon",
                answer="I ran Kafka at a weekend hackathon.",
                strength="partial",
            )
        ]
    )
    fixed = GOOD.model_copy(
        update={
            "terms": [
                *GOOD.terms,
                TermLink(term="Kafka", project="hackathon", fact_quote="I ran Kafka at a weekend hackathon."),
            ]
        }
    )
    graph, config, result = run_with_sources(FakeLLM(SCREEN, BRIEF, GAPPY, hit, fixed), tmp_path, stories)
    ask = result["__interrupt__"][0].value
    assert [p["source"] for p in ask["proposals"]] == ["stories.md"]
    result = graph.invoke(Command(resume={"confirmed": ["I ran Kafka at a weekend hackathon."]}), config)
    assert result["verdict"] == "READY", result["reasons"]


def test_invented_or_todo_quotes_are_dropped_not_proposed(tmp_path):
    bad = EvidenceList(
        items=[
            Evidence(
                gap=KAFKA_GAP,
                source="stories.md",
                quote="Led the Kafka migration",
                answer="x",
                strength="direct",
            ),
            Evidence(
                gap=KAFKA_GAP, source="facts.md", quote="I remember ~40 ms", answer="x", strength="partial"
            ),
        ]
    )
    _, _, result = run_with_sources(
        FakeLLM(SCREEN, BRIEF, GAPPY, bad), tmp_path, {"stories.md": "nothing here"}
    )
    assert result["__interrupt__"][0].value["proposals"] == []
    assert any("2 dropped" in line for line in result["log"])


def test_new_gap_from_a_replan_is_searched_and_asked_too(tmp_path):
    # real case (Field24 run 3, 2026-11-20): the re-plan after an answer brought up gaps never looked up
    answer = "RabbitMQ queue for webhooks at Northwind"
    replan = GOOD.model_copy(
        update={"terms": [*GOOD.terms, TermLink(term="Kafka", project="Northwind", fact_quote=answer),
                          TermLink(term="Go", project=None, fact_quote=None)]})  # fmt: skip
    llm = FakeLLM(SCREEN, BRIEF, GAPPY, NOTHING, replan, NOTHING)
    graph, config, result = run_with_sources(llm, tmp_path, {})
    assert result["__interrupt__"][0].value["gaps"] == [KAFKA_GAP]
    result = graph.invoke(Command(resume={"answers": [answer]}), config)
    ask = result["__interrupt__"][0].value
    assert ask["gaps"] == ["Go: which project or job shows this?"]  # only the new one
    assert [n for n, _ in llm.calls].count("EvidenceList") == 2
    result = graph.invoke(Command(resume={"answers": []}), config)
    assert result["verdict"] == "NOT_READY" and any("Go" in r for r in result["reasons"])
