# Interview contract and session ledger

Read this when a mock interview starts, resumes, or switches rounds. A one-off Predict list does not need a full ledger.

## Interview contract

Build the contract from the user's explicit request and the material on hand. Ask only when the missing information would materially change the drill; otherwise use these defaults and state them in one line:

```yaml
role: inferred from JD or resume; UNCONFIRMED if neither
seniority: inferred from JD (SWE II / Senior) or user background
round: technical            # recruiter_screen | technical | system_design | behavioral | onsite_loop
duration_minutes: 30
focus:
  resume_claims: 50
  role_fundamentals: 20
  scenario_or_system_design: 20
  behavioral: 10
feedback_policy: deferred   # deferred = realistic, feedback at the end; immediate = training, short feedback after each answer
hint_policy: on_request
max_followups_per_claim: 4
language: en                # questions and expected answers in English — the user will interview in English
```

- `feedback_policy=deferred`: realistic mock, feedback only at the end.
- `feedback_policy=immediate`: training mode, short evidence feedback after each question.
- `hint_policy=on_request`: hints only when the user asks.
- User-specified question type, duration, language, or feedback style overrides the defaults.
- For `behavioral`, shift focus to `behavioral: 60` and pull stories from the index in `career/stories.md`.

The contract is a session boundary, not a form to display. If the user says "just start", state round, duration, and feedback policy in one sentence and ask the first question.

## JD competency matrix

Avoid drilling only the resume and missing a hard requirement from the JD:

```text
| Role competency            | Resume evidence          | Status   | Interview action                            |
|----------------------------|--------------------------|----------|---------------------------------------------|
| Distributed state / ledger | Project A: idempotent event store | evidence | dig into implementation + failure handling  |
| Kubernetes / on-call       | none                     | gap      | scenario question; do not assume experience |
```

Status: `evidence / partial / none / UNCONFIRMED`. A competency with no resume evidence may be tested as fundamentals or as a scenario, but the user must never be led to pass it off as project experience.

## Session ledger

Keep minimal state inside the conversation:

```yaml
session:
  role: Software Engineer II, Backend
  round: technical
  feedback_policy: deferred
  question_count: 5
  elapsed_or_budget: 5/10 questions
  current_claim: project-a-idempotency

claims:
  - id: project-a-idempotency
    source: resume — "made the ingestion pipeline idempotent; replays produce identical state"
    status: partial
    evidence_found:
      - explained why idempotency was required (at-least-once delivery from the queue)
    missing:
      - how it was verified (test? replay? hash?)
      - what broke first before the change
    contradictions: []
    followup_depth: 2
    last_question_id: project-a-idempotency-02
```

Allowed claim statuses:

- `verified` — the required evidence is supported;
- `partial` — partly supported, with a specific gap;
- `unverified` — could not provide the minimum facts;
- `contradictory` — unresolved conflict with the resume or an earlier answer;
- `not_covered` — not asked this round.

The ledger records answer evidence, gaps, and status — never the model's guesses. It stays in the conversation by default; when the user asks to save it, confirm the path first (default: the role folder's `04-Interview-Prep.md`). Never write it into a public file.

## Resuming

When the user says "continue the last interview":

1. Use the ledger or stage summary already in the conversation.
2. If none exists, say so and ask the user to paste the last review or start over.
3. Never pretend to remember lost questions or answers.
4. Continue from the most recent unfinished claim or the highest-priority gap.
