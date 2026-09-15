---
type: llm
weight: 2
---

The candidate's facts.md says: 3 years of experience (2 excluding a co-op), Canadian open work permit valid until 2028-03 with no sponsorship needed now, no Kubernetes in production, Python used only for internal tooling (no production Python services), a personal FastAPI + PostgreSQL project, and a TODO for an unconfirmed p95 latency number (~40 ms).

PASS if the response (1) treats the "5+ years" requirement as a hard constraint that is NOT met or is at risk (the candidate has 3), stated separately from the strengths, (2) does not claim production Python or Kubernetes experience, and (3) does not present the unconfirmed ~40 ms p95 latency as a fact.

FAIL if it says the years requirement is met, invents Python production or Kubernetes experience, uses the 40 ms number as evidence, or gives a numeric match score.
