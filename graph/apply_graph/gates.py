"""Code checks for the interview-prep graph. No model calls: each function reads text and returns
what is wrong, so the graph's edges are decided by code, never by the model grading itself.
"""

from __future__ import annotations

import re
import tempfile
from pathlib import Path

from . import trace
from .prep_state import PREP_STAGES, Brief, Invite, Plan

# Phrases that give the point away before the interviewer asks (General Magic, 2026-11-20:
# "not very familiar with RAG" while memory-service is a hybrid-retrieval system with evals).
SELF_LIMITING = re.compile(
    r"not (?:very |that |really )?familiar|still (?:learning|working on)|I'?m not an expert|"
    r"don'?t have (?:much|a lot of) experience|not my strong",
    re.I,
)


MAX_PITCH_WORDS = 170  # about 60 seconds spoken

# Skills a posting can name, matched by code so a skill the plan forgets still becomes a gap.
# A posting's own "Skills:" line (Wellfound) is added on top. Keep patterns specific: "Go" alone is too vague.
SKILLS = {
    "Python": r"\bpython\b", "TypeScript": r"\btypescript\b", "JavaScript": r"\bjavascript\b",
    "Node.js": r"\bnode(\.?js)?\b", "React": r"\breact(\.js)?\b", "Next.js": r"\bnext\.?js\b",
    "Golang": r"\bgolang\b", "Rust": r"\brust\b", "Java": r"\bjava\b(?!script)", "C#": r"(?<!\w)c#",
    "C++": r"(?<!\w)c\+\+", "Kotlin": r"\bkotlin\b", "Swift": r"\bswift\b",
    "PostgreSQL": r"\bpostgres(ql)?\b", "MySQL": r"\bmysql\b", "MongoDB": r"\bmongo(db)?\b",
    "Redis": r"\bredis\b", "Kafka": r"\bkafka\b",
    "AWS": r"\baws\b", "GCP": r"\bgcp\b|google cloud", "Azure": r"\bazure\b", "Docker": r"\bdocker\b",
    "Kubernetes": r"\bkubernetes\b|\bk8s\b", "Terraform": r"\bterraform\b", "GraphQL": r"\bgraphql\b",
    "FastAPI": r"\bfastapi\b", "Django": r"\bdjango\b", "LangChain": r"\blangchain\b",
    "LangGraph": r"\blanggraph\b", "RAG": r"\brag\b|retrieval[- ]augmented",
    "MCP": r"\bmcp\b|model context protocol", "LLM": r"\bllms?\b", "Evals": r"\bevals?\b",
    "Fine-tuning": r"fine[- ]?tun", "Computer vision": r"computer vision",
    "PyTorch": r"\bpytorch\b", "Vector database": r"vector (db|database|store)|pgvector|pinecone|weaviate",
    "Sandboxed execution": r"\bsandbox", "Unity": r"\bunity\b(?! of)", "Unreal": r"\bunreal\b",
}  # fmt: skip


def _key(s: str) -> str:
    return re.sub(r"[^a-z0-9+#]", "", s.lower()).removesuffix("js") or s.lower()


def jd_skills(job_text: str) -> list[str]:
    """Skills the posting names: its own "Skills:" line plus every SKILLS pattern found in it. A saved
    03-Job-Description.md also holds our own match notes; only its "## Raw posting" part is the posting."""
    if m := re.search(r"^## Raw posting\s*$", job_text, re.M | re.I):
        job_text = job_text[m.end() :]
    found = [name for name, pat in SKILLS.items() if re.search(pat, job_text, re.I)]
    for line in job_text.splitlines():
        if line.lower().startswith("skills:"):
            found += [s.strip() for s in line.split(":", 1)[1].split(",") if s.strip()]
    out, seen = [], set()
    for s in found:
        if _key(s) not in seen:
            seen.add(_key(s))
            out.append(s)
    return out


def uncovered_skills(plan: Plan, job_text: str) -> list[str]:
    """Posting skills no plan term contains ("React.js" is covered by a term "TypeScript / React")."""
    term_keys = [_key(t.term) for t in plan.terms]

    def covered(s: str) -> bool:
        key = _key(s)
        forms = {key, key.removesuffix("s")} if len(key) >= 4 else {key}  # "LLMs" ~ "LLM", not "AWS" ~ "AW"
        return any(f in k for f in forms for k in term_keys)

    return [s for s in jd_skills(job_text) if not covered(s)]


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("’", "'").replace("“", '"').replace("”", '"')).strip().lower()


def quoted(quote: str | None, *sources: str) -> bool:
    """True if every piece of `quote` (split on ...) appears word for word in one of the sources."""
    if not quote or not quote.strip():
        return False
    pieces = [p for p in re.split(r"\.\.\.|…", quote) if p.strip()]
    hay = [_norm(s) for s in sources]
    return all(any(_norm(p) in h for h in hay) for p in pieces)


def check_stage(invite: Invite, invite_text: str) -> list[str]:
    problems = []
    if invite.stage == "UNCLEAR":
        problems.append("the email does not say which stage this is")
    if not quoted(invite.evidence, invite_text):
        problems.append(f"stage evidence is not in the email: {invite.evidence!r}")
    return problems


def stage_route(invite: Invite, problems: list[str]) -> str:
    if problems:
        return "confirm"
    return "prep" if invite.stage in PREP_STAGES else "stop"


def filter_brief(brief: Brief, research_text: str) -> tuple[Brief, list[str]]:
    """Keep only research claims whose quote is really in the research text."""
    dropped: list[str] = []

    def keep(claims):
        out = []
        for c in claims:
            if quoted(c.quote, research_text):
                out.append(c)
            else:
                dropped.append(c.text)
        return out

    kept = Brief(
        product=keep(brief.product), current_bet=keep(brief.current_bet), interviewer=keep(brief.interviewer)
    )
    return kept, dropped


def check_plan(
    plan: Plan, facts_text: str, user_facts: list[str], out_dir: str | None = None, job_text: str = ""
) -> list[str]:
    """Problems that send the plan back to the model. Missing evidence is not a problem here; it is a gap."""
    sources = [facts_text, *user_facts]
    confirmed = [confirmed_only(facts_text), *user_facts]
    problems = []
    if _norm(plan.lead_project) not in _norm(facts_text):
        problems.append(f"lead project {plan.lead_project!r} is not named in facts.md")

    def check_quote(label: str, quote: str | None) -> None:
        if not quote or quoted(clean_quote(quote), *confirmed):
            return
        if quoted(quote, *sources):
            problems.append(f"{label}: quote comes from a TODO (unconfirmed) line: {quote!r}")
        else:
            problems.append(f"{label}: quote is not in facts.md: {quote!r}")

    for t in plan.terms:
        check_quote(f"term {t.term!r}", t.fact_quote)
    for q in plan.questions:
        check_quote(f"question {q.question!r}", q.fact_quote)
    if m := SELF_LIMITING.search(plan.pitch):
        problems.append(f"pitch talks itself down: {m.group(0)!r}")
    if (n := len(plan.pitch.split())) > MAX_PITCH_WORDS:
        problems.append(f"pitch is {n} words; cut it to {MAX_PITCH_WORDS} or fewer (about 60 seconds spoken)")
    if missing := uncovered_skills(plan, job_text):
        problems.append(
            "the posting names these skills but the plan has no term for them; add each as a term "
            f"(project and fact_quote null if nothing shows it): {', '.join(missing)}"
        )
    problems += [
        f"pitch number not in facts.md: {f['claim']}" for f in pitch_numbers(plan.pitch, sources, out_dir)
    ]
    return problems


def clean_quote(quote: str) -> str:
    """What a quote can prove: a leading list marker dropped, anything from `TODO:` on cut off. A quote of
    a whole facts.md line still counts for its confirmed part; a quote of only the TODO part becomes empty."""
    q = re.sub(r"^\s*[-*]\s+", "", quote)
    return q.split("TODO:")[0].rstrip(" `")


def confirmed_only(facts_text: str) -> str:
    """facts.md with everything after each `TODO:` cut off: what follows a TODO is a question, not evidence.
    A confirmed line that ends with a TODO about a detail keeps its confirmed part."""
    return "\n".join(line.split("TODO:")[0].rstrip(" `") for line in facts_text.splitlines())


def pitch_numbers(pitch: str, sources: list[str], out_dir: str | None) -> list[dict]:
    """Reuse the resume trace gate on the pitch: every number must exist in facts (or a user answer)."""
    # the run folder may not exist yet (it is created by write_prep); fall back to the system temp dir
    with tempfile.TemporaryDirectory(dir=out_dir if out_dir and Path(out_dir).is_dir() else None) as d:
        f = Path(d) / "pitch.md"
        f.write_text(pitch, encoding="utf-8")
        return trace.check(f, "\n".join(sources))


def find_gaps(plan: Plan) -> list[str]:
    """Terms and questions with nothing behind them: ask the candidate, never write 'not familiar'."""
    gaps = [f"{t.term}: which project or job shows this?" for t in plan.terms if not t.fact_quote]
    gaps += [f"{q.question} (needs: {', '.join(q.must_cover)})" for q in plan.questions if not q.fact_quote]
    return gaps


def fill_from_evidence(plan: Plan, hits: list) -> Plan:
    """Put verified facts.md hits into the term / question their gap came from. A partial hit is labelled."""
    by_gap = {e.gap.strip(): e for e in hits}
    terms = []
    for t in plan.terms:
        e = by_gap.get(f"{t.term}: which project or job shows this?")
        if e and not t.fact_quote:
            label = "facts.md" + (" (partial)" if e.strength == "partial" else "")
            t = t.model_copy(update={"fact_quote": e.quote, "project": t.project or label})
        terms.append(t)
    questions = []
    for q in plan.questions:
        e = by_gap.get(f"{q.question} (needs: {', '.join(q.must_cover)})")
        questions.append(q.model_copy(update={"fact_quote": e.quote}) if e and not q.fact_quote else q)
    return plan.model_copy(update={"terms": terms, "questions": questions})


def sort_evidence(items: list, facts_text: str, sources: dict[str, str]) -> tuple[list, list, list[str]]:
    """Split what find_evidence returned: (confirmed facts.md hits -> used without asking, hits in other
    files -> proposed to the candidate, dropped -> quote not found where the model said it was)."""
    from_facts, proposals, dropped = [], [], []
    for e in items:
        if e.strength == "none" or not e.quote:
            continue
        if e.source == "facts.md":
            q = clean_quote(e.quote)
            if quoted(q, confirmed_only(facts_text)):
                from_facts.append(e.model_copy(update={"quote": q}))
            else:
                dropped.append(e)
        elif e.source in sources and quoted(e.quote, sources[e.source]):
            proposals.append(e)
        else:
            dropped.append(e)
    return from_facts, proposals, [f"{e.gap}: quote not found in {e.source}" for e in dropped]


def readiness(state: dict) -> tuple[str, list[str]]:
    """READY only when the stage is verified, the plan passed its checks and no question is uncovered."""
    reasons = []
    if state.get("problems"):
        reasons += [f"unfixed: {p}" for p in state["problems"]]
    if state.get("gaps"):
        reasons += [f"no evidence yet: {g}" for g in state["gaps"]]
    if not state.get("brief") or not (state["brief"].product or state["brief"].current_bet):
        reasons.append(
            "no verified research on what the product does; the lead project was picked from the JD only"
        )
    return ("READY" if not reasons else "NOT_READY"), reasons
