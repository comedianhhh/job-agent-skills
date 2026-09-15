# Resume bullet few-shots (domain-neutral)

This file constrains the *shape* of resume bullets. It provides no copyable project material. Learn only the organisation "problem / evolution → action → mechanism → constraint → result"; copying any project name, number, technology combination, or business scenario from here is forbidden.

## Rules of use

Fixed generation order:

1. Extract 4–6 candidate pillars from the project facts.
2. For each pillar fill in: core tension, my action, mechanism, constraints, result, evidence.
3. Write the top-level bullet against the positive examples below.
4. Rewrite against the negative-example checklist.
5. Check that each bullet naturally yields one interview main question: "why this design / how was it traded off / how was it verified".

Few-shots align expression; they never replace repo evidence. When the project has no real metric, write an architectural result verifiable in code and mark unmeasured production benefit `to measure` / `to verify`; never add a number to imitate the examples. The final gate is still `career/rules.md` and traceability to `career/facts.md`.

## Positive: layered mechanism

**Abstract project facts**

- Handling logic was scattered across several entry points; every new scenario meant repeated edits to the main flow.
- The candidate owned unified error handling and took part in the main-path refactor.
- The code has classified handling, bounded retries, and a degradation path.

**Acceptable bullet**

> **Layered fault tolerance:** Consolidated error handling that was scattered across entry points — and that made every new scenario a risky edit to the main path — into a layered mechanism: bounded retry, degradation, or fail-fast chosen by error class, with one observable outcome format; reduced the main-path surface touched by new scenarios. Production impact to be verified against a baseline.

**Why it passes**

- Core tension first, then the owned change.
- The mechanism is explained, not a list of technology names.
- Result and mechanism are causally linked.
- Unprovable benefit is not stated as fact.

## Positive: architectural evolution

**Abstract project facts**

- The old approach was a fixed sequence of steps; adding a capability meant editing several nodes.
- The candidate led the move from a fixed pipeline to extensible orchestration.
- The new design plugs different implementations in through one interface while keeping boundary constraints.

**Acceptable bullet**

> **Extensible orchestration:** Led the rework of a fixed step-sequence pipeline into an extensible orchestration structure — a single capability interface with differentiated implementations pushed to independent extension points, keeping input validation, timeout, and failure-isolation boundaries — so new implementations attach at extension points without touching the core scheduling logic.

**Why it passes**

- "Old → new" forms a clear evolution.
- Abstraction, extension points, and core boundaries are named.
- The result is a verifiable architectural effect, not "improved efficiency".
- No file or function names in the top-level bullet.

## Negative: ticket-style features

```text
- Added list pagination and filtering, improved loading experience (to measure).
- Built the error dialog to handle API exceptions.
- Added caching and retry logic to improve API stability.
```

**Why it fails**

- No original problem or evolution context.
- "Added / built" gives no personal boundary.
- No mechanism, constraint, or failure boundary.
- "Improved experience / stability" is unverifiable.
- Stays at feature level; cannot support architecture-level follow-ups.

## Rewrite: from implementation action to engineering pillar

**Original**

> Added caching and retry, optimised API requests.

**Acceptable rewrite**

> **Request reliability:** Addressed duplicate requests and latency amplification caused by downstream jitter with caching, timeouts, and bounded retry — retrying only idempotent requests with a max count and back-off ceiling to prevent retry storms during incidents; non-idempotent requests fail fast or degrade. Latency benefit to be verified against a baseline.

**Rewrite moves**

1. Turn "optimised requests" back into a failure mode that can be questioned.
2. Turn technology names into mechanism plus applicability boundary.
3. Add the constraints: retry count, back-off, idempotency.
4. Turn unevidenced effect into a verification plan rather than an invented metric.

## Hard checks after generation

- [ ] Every top-level bullet starts with `**<Generic pillar name>:**`; the pillar is an architectural / engineering capability an interviewer understands, not a private class or function name.
- [ ] One pillar per bullet; no lists of parallel features.
- [ ] Each has at least "problem or evolution + mechanism + result"; key pillars add constraints or numbers where real.
- [ ] The result follows the mechanism and answers "what changed in the system after adopting it".
- [ ] With no metric, write the architectural result; never substitute "improved performance / stability / experience".
- [ ] Real metrics come only from the user's material, the repo, or an explicit measurement.
- [ ] Private functions, paths, internal enums, and jargon appear only in the source-evidence index.
- [ ] Implementation names (`RunManager`, `StreamBridge`, `execution id`) are not pillar names; rewrite as "run management", "streaming event bridge", "server-side run identifier".
- [ ] Ownership verbs match the real scope; a partial contribution is not inflated to owner.
- [ ] Each bullet yields a main question on motivation, trade-off, boundary, or verification.
- [ ] No project names, numbers, domain nouns, or metrics copied from any example.
