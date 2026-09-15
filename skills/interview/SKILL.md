---
name: interview
description: Resume- and JD-driven interview prediction, mock interview with contract-based follow-up questioning, evidence review, and weak-spot retry, structured around North American rounds (recruiter screen, OA, technical, system design, behavioral). Use when the user types /interview, asks to predict questions, run a mock or stress interview, drill a resume claim, practise system design or STAR answers, or check how well they can defend what the resume says.
---

# /interview — Interrogate the resume

`/interview` does not write answers to recite. It turns the important claims on the resume and in the JD into verifiable questions, and checks — through an interview contract, one question at a time, evidence scoring, and targeted retry — whether the user can explain real responsibilities, implementation, metric definitions, trade-offs, and failures.

```text
resume / JD → claims + role-competency matrix → interview contract → question & scoring contract
           → one question at a time, dynamic follow-ups → session ledger → evidence review + retry
```

## Inputs

1. The role's resume (`<folder>/01-Resume.html`) and `career/facts.md` — including its `TODO:` lines, which are exactly the numbers an interviewer will probe.
2. The JD (`<folder>/03-Job-Description.md`).
3. `career/stories.md` (`[fact]` vs `[draft — confirm]`).
4. Round, time available, feedback preference.

No JD → predict from the resume. No resume → ask for one project. Ask only for what materially changes the drill; otherwise use defaults. Unknowns are `UNCONFIRMED`; never fabricate experience, numbers, or technical detail. Save a review to disk only on request (default: the role's `04-Interview-Prep.md`); never into a public file.

## North American rounds

| Round | Tests | Default focus |
|---|---|---|
| Recruiter screen | 60-second pitch, authorization, comp, motivation | intro script, logistics |
| OA / coding | DS&A, take-home | out of scope unless asked |
| Hiring-manager / phone technical | one project end-to-end | Ownership + Technical + Architecture claims |
| Onsite — coding | live coding | out of scope unless asked |
| Onsite — system design | one subsystem in depth for mid-level; breadth + trade-offs for senior | `references/scenario-interviews.md` |
| Onsite — behavioral | STAR, conflict, failure, leadership | `stories.md` index |
| Onsite — HM / bar raiser | consistency with everything already said | ledger contradictions |

## Modes

### Predict — `/interview predict`
Extract Ownership / Metric / Technical / Architecture / Result claims; build `competency — evidence — gap` from the JD; rank by relevance × probability × wording risk × evidence gap; output high-probability, supplementary, and stress questions. Per core question: source, intent, facts the answer must cover, next follow-up. No long model answers.

```text
Q: Why did you choose an event-sourced store instead of updating rows in place?
Source: resume — "designed the ingestion pipeline … replayable"
Intent: technical choice, decision authority, trade-off
Answer must cover: original problem, alternatives, why this one, your part, result evidence
Follow-up: what breaks first at 10× the event volume?
```

### Grill — `/interview grill`
Build the contract ([references/interview-contract-and-session.md](references/interview-contract-and-session.md)); lock a scoring contract before each question ([references/question-and-scoring-contract.md](references/question-and-scoring-contract.md)); **one question per turn**; dig / clarify / step down / switch / end based on evidence; feedback per policy (immediate = training, deferred = realistic); keep the ledger. Scenario or system design → [references/scenario-interviews.md](references/scenario-interviews.md). Never give the answer before the user answers; hints only as agreed, never project facts.

### Review — `/interview review`
From the ledger: verified / partial / unverified / contradictory claims with the answer evidence; what needs a fact, knowledge, or toned-down wording; the two follow-ups most likely to expose the user; prioritised actions. No total score. Template: [references/review-and-retry.md](references/review-and-retry.md).

### Retry — `/interview retry`
Only `partial` / `unverified` / `contradictory` claims; variants and counterfactuals, not repeats; compare evidence with last time; passed claims leave the queue.

## Claims and what to probe

- **Ownership** — personal scope, what you built by hand, decisions, team split. Project result ≠ personal result.
- **Metric** — baseline, denominator, period, data source, attribution.
- **Technical** — inputs/outputs in *this* project, why this technique, the trade-off. Definitions do not count.
- **Architecture** — components, data flow, boundaries, alternatives, failure handling, scaling limits.
- **Result** — shipped or not, who uses it, how measured, personal vs. team.

Chase first: vague verbs without object/evidence; numbers without a measurement definition; "led / architected" without a boundary; happy path only; term definitions without project role; contradictions with the resume or earlier answers.

```text
sufficient → ≤ 1 alternative / counterfactual → close claim
partial    → probe only the critical missing piece
no idea    → step down to the smallest fact → still nothing → unverified, switch
two answers with no new evidence → stop the branch
budget reached → wrap up → Review
```

When the resume is stronger than the user can defend, offer exactly three paths: add a real fact, learn the missing knowledge, or tone the wording down. Changes to `facts.md` / `stories.md` only with confirmation.

## Sequence

`/job-match → /great-resume → /make-resume → /job-apply → /interview → /offer`. The resume is written for the recruiter; the follow-ups are reserved for the facts.
