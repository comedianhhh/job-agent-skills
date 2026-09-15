# Scenario and system design questions

Read this when the user is asked to design a system, scope a take-home, handle a business case, or reason in an unfamiliar domain. For SWE II backend loops (payments, ledgers, gateways, search), the interviewer usually wants depth on one subsystem more than breadth.

## Answer skeleton

Guide the user through these relationships; do not force a header-by-header recitation:

```text
users and business outcome
  ↓
minimum scope and explicit non-goals
  ↓
inputs, outputs, success criteria (SLOs, consistency, correctness)
  ↓
data model, APIs, state, workflow
  ↓
failure handling, idempotency, permissions, human override
  ↓
observability and test / evaluation set
  ↓
delivery plan and acceptance gates
```

## Clarifying questions to insist on

1. Does the system only recommend, or does it execute real side effects (money moves, orders placed, state written)?
2. What is the worst possible error, and does it need a hard veto / kill switch?
3. Where does ground truth come from — deterministic rules, a system of record, a domain expert, human labelling?
4. What existing APIs, data, devices, or deployment constraints exist?
5. Scale numbers: QPS, data volume, fan-out, latency budget, read/write ratio.

In an unfamiliar industry, the user should not pretend to know the business rules. A good answer explains how a domain expert supplies ground truth and how that becomes versioned, executable, regression-tested acceptance criteria.

## Two-week take-home / demo scoping

Check the user:

- picks one real end-to-end loop, not a generic platform;
- gets end-to-end working in week one, then failure paths, tests, docs, and demo in week two;
- mocks external dependencies that are not ready;
- keeps high-risk writes read-only or behind confirmation;
- keeps a runnable build every day;
- explicitly rejects multi-agent complexity, full platform coverage, and UI unrelated to acceptance.

Follow-ups:

- Why is this scope achievable in two weeks?
- Which dependency is most likely to block, and what is the degraded path?
- How do you prove it is not a one-time happy path?
- If only one week remained, what gets cut?

## Backend / distributed-systems judgement

Check whether the design pushes correctness where it belongs: deterministic computation, permissions, money, database constraints, and safety boundaries live in code or the system of record, not in a model or a client. Where the user's own experience applies, expect it to be used: authoritative state + reconciliation, idempotent commands, deterministic replay, load testing with a headless harness, tick-latency instrumentation.

Services should have single responsibility, structured inputs, and stable outputs; side-effecting operations should address permissions, idempotency, confirmation, audit, and recovery.

## AI / agent systems (when the role calls for it)

Do not let the LLM own everything. Models handle semantic understanding, extraction, candidate planning, unstructured content; code handles determinism, permissions, amounts, constraints. Tools have single responsibility, structured parameters, stable returns; side-effecting tools add permission, idempotency, confirmation, audit, recovery.

## Acceptance

Cover at least:

- core task completed;
- structured outputs and parameters correct;
- safe behaviour with no evidence, missing parameters, or external failure;
- normal, edge, error, and adversarial cases where relevant;
- model / prompt / tool trace / latency / cost observable (AI systems), or metrics / traces / alerts (backend);
- hard gates on high-risk errors.

"The demo runs" and "the answer looks fine" are not acceptance results.
