from __future__ import annotations

import operator
from typing import Annotated, Literal, TypedDict

from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from pydantic import BaseModel, Field


class Requirement(BaseModel):
    requirement: str
    evidence: str | None = Field(description="Quote from facts.md that covers it, or null if nothing does")


class Match(BaseModel):
    decision: Literal["APPLY", "SKIP"]
    reason: str = Field(description="One sentence; for SKIP, the hard constraint that failed")
    requirements: list[Requirement]


class CompanyBrief(BaseModel):
    product: str = Field(description="What the company sells or builds, one sentence")
    team_focus: str = Field(description="What this role's team works on, one sentence")
    values: list[str] = Field(description="Things the posting stresses (practices, culture, priorities)")


class CoverLetter(BaseModel):
    body: str = Field(description="Cover letter body in Markdown, no greeting block or signature")


Status = Literal["READY", "SKIPPED", "BLOCKED", "REJECTED"]


class ApplyState(TypedDict, total=False):
    # inputs
    job_text: str
    facts_text: str
    out_dir: str
    # produced by nodes
    match: Match
    company: CompanyBrief
    draft: str
    findings: list[dict]
    attempts: int
    feedback: str | None
    status: Status
    # every node appends one line; the reducer concatenates instead of overwriting
    log: Annotated[list[str], operator.add]


# Checkpoints may only rebuild these models (plus LangGraph's own safe types), so a run resumes the
# same way whether or not LANGGRAPH_STRICT_MSGPACK is set. Add any new model that goes into the state.
SERDE = JsonPlusSerializer(
    allowed_msgpack_modules=[(__name__, cls.__name__) for cls in (Match, Requirement, CompanyBrief)]
)
