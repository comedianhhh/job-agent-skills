"""State and model outputs for the interview-prep graph (prep.py)."""

from __future__ import annotations

import operator
from typing import Annotated, Literal, TypedDict

from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from pydantic import BaseModel, Field

Stage = Literal["APPLIED", "SCREEN", "OA", "TECH", "ONSITE", "OFFER", "REJECTED", "UNCLEAR"]
PREP_STAGES = {"SCREEN", "TECH", "ONSITE"}  # stages that get an interview prep


class Invite(BaseModel):
    stage: Stage = Field(description="What the email moves the application to; UNCLEAR if it does not say")
    evidence: str = Field(description="The sentence from the email that shows the stage, copied exactly")
    when: str | None = Field(default=None, description="Interview date/time with timezone if stated")
    interviewer: str | None = Field(default=None, description="Name and title of the interviewer if stated")


class Claim(BaseModel):
    text: str = Field(description="One short fact in your own words")
    quote: str = Field(
        description="The research text that supports it, copied exactly (may shorten with ...)"
    )


class Brief(BaseModel):
    product: list[Claim] = Field(description="What the product actually does today, for whom")
    current_bet: list[Claim] = Field(description="What they are pushing right now (recent posts, launches)")
    interviewer: list[Claim] = Field(description="Interviewer's background and own projects")


class TermLink(BaseModel):
    term: str = Field(description="A skill or concept the JD or product leans on (e.g. RAG, evals)")
    project: str | None = Field(description="The candidate's project or job that shows it, or null")
    fact_quote: str | None = Field(description="The facts line that proves it, copied exactly, or null")


class Question(BaseModel):
    question: str
    intent: str = Field(description="What the interviewer is really checking")
    must_cover: list[str] = Field(description="Facts the answer has to hit")
    fact_quote: str | None = Field(description="Main facts line the answer rests on, copied exactly, or null")


class Plan(BaseModel):
    lead_project: str = Field(description="Project or job name exactly as it appears in facts")
    lead_reason: str = Field(description="Why this one, tied to what the product does (not the JD stack)")
    terms: list[TermLink]
    questions: list[Question]
    pitch: str = Field(description="60-second spoken intro, short sentences, numbers only from facts")


class Evidence(BaseModel):
    gap: str = Field(description="The gap, copied as given")
    source: str = Field(description="File the quote is from (e.g. facts.md, stories.md, blocks.md), or none")
    quote: str | None = Field(description="Text from that file, copied exactly, or null")
    answer: str | None = Field(
        description="One first-person sentence the candidate could confirm, built only from the quote; "
        "for a partial match say what it does not cover. Null if nothing found."
    )
    strength: Literal["direct", "partial", "none"]


class EvidenceList(BaseModel):
    items: list[Evidence]


class PrepState(TypedDict, total=False):
    # inputs
    invite_text: str
    job_text: str
    research_text: str  # company site / blog / interviewer profile, pasted or saved; untrusted
    facts_text: str
    out_dir: str
    career_dir: str  # optional: enables the compact node (closed applications -> archive.md)
    sources: dict[str, str]  # optional: other candidate files to search for gaps {"stories.md": text, ...}
    # produced by nodes
    invite: Invite
    stage: Stage
    brief: Brief
    dropped: list[str]  # research claims whose quote was not in the research text
    plan: Plan
    problems: list[str]
    gaps: list[str]
    user_facts: list[str]  # answers the candidate gave or confirmed at the gap interrupt
    seen_gaps: list[str]  # gaps already searched (and asked if still open)
    open_gaps: list[str]  # what the current ask_gaps round asks
    gap_rounds: int
    proposals: list[Evidence]  # found outside facts.md: shown pre-filled, the candidate confirms
    facts_hits: list[Evidence]  # found in confirmed facts.md: code fills them into every plan
    attempts: int
    feedback: str | None
    verdict: Literal["READY", "NOT_READY", "STOPPED"]
    reasons: list[str]
    compacted: list[str]  # archive lines written by the compact node
    spans: Annotated[
        list[dict], operator.add
    ]  # one per finished node: {node, ms, input_tokens, output_tokens}
    log: Annotated[list[str], operator.add]


SERDE = JsonPlusSerializer(
    allowed_msgpack_modules=[
        (__name__, cls.__name__)
        for cls in (Invite, Claim, Brief, TermLink, Question, Plan, Evidence, EvidenceList)
    ]
)
