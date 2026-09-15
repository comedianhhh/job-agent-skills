---
description: A full JD with one hard-constraint miss (5+ years vs 3) and one real gap (Kubernetes). The skill should produce the requirement–evidence matrix from facts.md, not from vibes, and give a verdict without a percentage.
tags: [job-match, judge]
max_turns: 15
allowed_tools: [Read, Glob, Grep, Skill]
expected_outcome: Requirement–evidence matrix citing facts.md sections, hard constraints listed separately with the years mismatch called out, Kubernetes marked REAL GAP, a verdict from the fixed set, no match percentage.
---

My job-search workspace (facts.md, answers.yaml, targets.yaml, tracker.md) is in a `career/` folder — either `./career` in the working directory or a `resources/career` directory you were given read access to; use Glob to find `facts.md` if it isn't in the working directory.

Is this role worth applying to? Here's the posting:

---
**Senior Backend Engineer — Platform**
Orbital Freight · Toronto, ON (hybrid, 2 days/week) · CAD 150,000–180,000

We run the tracking backbone for 300+ carriers. You'll own services that ingest carrier events at scale and keep our shipment state correct.

What you'll do
- Design and operate event-driven services in Python (FastAPI) and Go
- Own our Kubernetes deployments (EKS) and the on-call rotation for ingestion
- Lead design reviews and mentor two junior engineers

What we need
- 5+ years of professional backend experience
- Production Python; Go a strong plus
- Deep PostgreSQL experience (partitioning, tuning)
- Hands-on Kubernetes in production
- Experience with idempotent, exactly-once-ish event processing

Nice to have
- Kafka, Terraform, prior logistics/fintech domain

You must be legally authorized to work in Canada. We do not sponsor visas.
---
