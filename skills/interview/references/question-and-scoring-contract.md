# Question and scoring contract

Read this in Grill mode before asking a question and before evaluating an answer.

## Lock the criteria first

Every core question gets an internal scoring contract *before* it is asked. The contract may not be redefined after seeing the answer to fit an impression; if the question itself turns out to be vague, clarify or discard it.

```yaml
question_id: project-a-queue-01
claim_id: project-a-hybrid-search
question: Why combine keyword and vector retrieval instead of using one of them?
intent: verify architecture understanding, trade-off, personal boundary
required_evidence:
  - what each retrieval path solves and where one alone failed
  - the fusion rule and why it was chosen
  - which part the user implemented personally
followup_triggers:
  - lists nouns with no data flow
  - cannot name an alternative
  - counts an upstream library or vendor capability as personal work
stop_condition:
  - required evidence supported, plus at most one counterfactual follow-up
```

Lighter contracts are fine for fundamentals questions, but every question must have a stated intent and pass evidence.

## Judging after the answer

Use evidence status, never an uncalibrated precise score:

```text
Status: partial

Answered:
- Explained the two retrieval paths and where each fails alone.
- Explained the fusion rule.

Still missing:
- Did not state which code path was personally written.

Next:
- Ask for the personal implementation boundary.
```

Under `deferred`, do not read the judgement aloud after each question — update the ledger and keep asking like a real interviewer. Natural transitions are fine; do not reveal the rest of the question tree.

## Dynamic follow-ups

- One required item missing → probe only that one.
- Answer sufficient → one alternative, scaling-limit, or counterfactual question, then close the claim.
- Answer sounds rehearsed → switch to concrete inputs, a code path, a failure, or a data flow from the project.
- Answer clearly exceeds the real experience → ask for the boundary: personal vs. team, upstream vs. own work.
- Answer stuck → structural hint per the hint policy; never supply project facts.
- Two answers with no new evidence → stop spending; mark `unverified` or `partial`.

## Follow-up question types

Pick as needed; do not walk through all of them mechanically:

```text
Context:        why was it needed?
Ownership:      what exactly did you personally own?
Structure:      components, data flow, boundaries?
Implementation: how does the key code or process actually work?
Decision:       why this choice?
Alternative:    why not the other approach?
Failure:        what went wrong, how was it reproduced and fixed?
Metric:         baseline, sample, period, and how it was measured?
Cost:           what did the approach give up?
Retrospective:  what would you change doing it again?
```

## Spoken delivery

When the user practises out loud or provides a transcript, additionally observe:

- conclusion first?
- does a project answer close within the agreed time (30-second version first — `career/stories.md` rule)?
- filler connectors with no information?
- stacked technology names with no actions or evidence?
- team results narrated as personal?

Evaluate structure and information density only — never accent, voice, personality, or anything unrelated to the role.
