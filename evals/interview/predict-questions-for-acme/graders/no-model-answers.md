---
type: 'llm'
weight: 2
---

You can't open the candidate's files, so here they are (fictional persona Jordan Lee). They are the only facts. The application folder's 01-Resume.html is still the blank template.

<!-- fixture-sources: facts.md blocks.md stories.md tracker.md 2026-09-02-Acme-Backend-Engineer-4471/03-Job-Description.md -->
**career/facts.md**, verbatim:

````markdown
# Facts — single source of truth (FICTIONAL eval persona: Jordan Lee)

> Only things that actually happened. Every tailored resume picks, orders, and rewords from here and never adds a fact.
> Mark anything unconfirmed with `TODO:`. Unconfirmed facts never reach an outgoing document.

## Basics
- Name: Jordan Lee
- Toronto, ON | (416) 555-0142 | jordan.lee.dev@example.com
- LinkedIn: linkedin.com/in/jordan-lee-example | GitHub: github.com/jordanlee-example
- Work authorization: Canada, open work permit valid until 2028-03, no sponsorship needed now; would need sponsorship after 2028-03. Not authorized to work in the US.

## Education
| Dates | School | Program / degree |
|---|---|---|
| 2019-09 – 2023-04 | University of Waterloo | BASc Computer Engineering |

## Experience

### Northwind Logistics — Toronto (hybrid) | 05/2023 – Present
**Title:** Software Engineer (Backend)
**Stack:** C# / .NET 8, ASP.NET Core, PostgreSQL, Redis, RabbitMQ, Docker, GitHub Actions, Azure App Service
**Product / team size / external anchors:** shipment-tracking platform used by ~40 freight customers; team of 6 engineers; Northwind is a Deloitte Fast 50 company (2024, verifiable).

Facts (one per line; numbers with their denominator and period):
- Owned the shipment-events ingestion service end to end (design, implementation, on-call): consumes carrier webhooks, deduplicates by idempotency key, writes an append-only event log in PostgreSQL, projects current shipment state.
- Replaced a cron-based polling sync with the webhook + event-log design; reduced median "carrier update → visible in dashboard" latency from ~15 minutes to under 30 seconds (measured over March 2025 on the production dashboard metrics; 100% of shipment updates).
- Added idempotency keys and a reconciliation job that re-derives state from the event log; duplicate-update incidents went from 3–4 per month (Q4 2024 incident log) to 0 in the six months after (Jan–Jun 2025).
- Wrote the integration test suite for the ingestion service (xUnit + Testcontainers for PostgreSQL); 140 tests, runs in CI on every PR.
- Team result (not personal): the platform's uptime for 2025 H1 was 99.95% — team-wide, do not claim personally.
- `TODO:` p95 ingestion latency — I remember ~40 ms but have not found the dashboard export; do not use the number until confirmed.
- Python: wrote internal tooling only (a CLI to replay carrier webhooks from S3 logs, ~600 lines, Click + boto3). No production Python services.
- No Kubernetes in production: Azure App Service deployments; read about K8s, never operated a cluster.

### Blue Maple Games — Waterloo (co-op, full-time) | 01/2022 – 08/2022
**Title:** Software Developer Co-op
**Stack:** Unity, C#, Node.js
- Built the in-game inventory sync between a Unity client and a Node.js backend (REST); shipped in a mobile game with ~50k downloads (team result; my part was the client-side sync module and the retry logic).
- `TODO:` exact release date of the game version that included my work.

## Projects
### ledger-lite (personal, public on GitHub, 2025)
- FastAPI + PostgreSQL double-entry ledger: idempotent `POST /transfers`, append-only postings, explicit state machine (initiated → submitted → settled/returned). Owned entirely. ~1,200 lines Python, 60 pytest tests, GitHub Actions CI. Not used by anyone but me.

## Shipped / public artifacts
- github.com/jordanlee-example/ledger-lite (public)
- Northwind shipment-events ingestion service (production since 2024-11; internal, not public)

## Iron rules
1. No number without a source. No source → say it qualitatively or not at all.
2. "Led / owned / architected" only where you can explain the decision, the delivery, and the result under follow-up.
3. Team work is written as team work. Your bullets carry your work; the company line carries borrowed names.
4. Unreleased work: describe what was built, never the outcome. Shipped work must say shipped.
5. One fact, one place.
````

**career/blocks.md**, verbatim:

````markdown
# Blocks — finished, copy-ready bullets (fictional eval persona)

## Northwind — ingestion
- **NW-1** Owned the shipment-events ingestion service end to end (C#/.NET 8, PostgreSQL, RabbitMQ): carrier webhooks → idempotent append-only event log → projected shipment state; on-call for it since launch (Nov 2024).
- **NW-2** Replaced cron polling with webhook ingestion + event log, cutting median carrier-update-to-dashboard latency from ~15 min to <30 s across all shipment updates (Mar 2025 production metrics).
- **NW-3** Eliminated duplicate-update incidents (3–4/month in Q4 2024 → 0 in Jan–Jun 2025) with idempotency keys and a reconciliation job that re-derives state from the log.
- **NW-4** Built the service's integration suite (xUnit + Testcontainers, 140 tests) running on every PR in GitHub Actions.

## Projects
- **LL-1** ledger-lite (personal): FastAPI + PostgreSQL double-entry ledger with idempotent transfers, append-only postings, and an explicit transfer state machine; 60 pytest tests, CI on GitHub Actions.
````

**career/stories.md**, verbatim:

````markdown
# Stories (fictional eval persona)

## Failure — the duplicate-update incident (Jan 2025) [fact]
Situation: a carrier re-sent a batch of 2,000 webhooks after their outage; our sync applied them twice and customers saw shipments flip back to "in transit".
Task: stop the bleeding, then make it impossible.
Action: I paused the consumer, wrote the reconciliation job that re-derives state from the event log, then added idempotency keys on the webhook id + carrier.
Result: state corrected within the hour; zero duplicate incidents in the following six months.

## Trade-off — event log vs updating rows in place [fact]
Chose append-only events + projection over in-place updates so we could replay and audit; cost was more storage and a projection job to maintain.

## Conflict — pushing back on a deadline [draft — confirm]
Draft only; details not yet confirmed with Jordan.
````

**career/tracker.md**, verbatim:

````markdown
# Pipeline (fictional eval persona)

Statuses: `DRAFT` → `APPLIED` → `SCREEN` → `OA` → `TECH` → `ONSITE` → `OFFER` / `REJECTED` / `GHOSTED` / `WITHDRAWN`; `BLOCKED` = materials ready but a hard constraint is unresolved — do not apply.

Follow-up rule: 10 business days after `APPLIED` with no reply → one LinkedIn message; about 2 more weeks of silence → `GHOSTED`.

| Company | Role | Req | Location | Applied | Status | Next step | Folder |
|---|---|---|---|---|---|---|---|
| Acme Corp | Backend Engineer, Payments | Greenhouse 4471 | Toronto (hybrid) | 2026-09-02 | `APPLIED` | follow up on LinkedIn 2026-09-16 | [2026-09-02-Acme-Backend-Engineer-4471](2026-09-02-Acme-Backend-Engineer-4471/) |
| Northstar Robotics | Software Engineer, Platform | Ashby 9b2f | Remote Canada | 2026-09-08 | `SCREEN` | recruiter call 2026-09-17 10:00 ET | [2026-09-08-Northstar-Software-Engineer-Platform](2026-09-08-Northstar-Software-Engineer-Platform/) |
| Maple Bank | Developer II | Workday R-2210 | Toronto (onsite) | — | `DRAFT` | Jordan applies on Workday | [2026-09-10-Maple-Bank-Developer-II-R2210](2026-09-10-Maple-Bank-Developer-II-R2210/) |
````

**career/2026-09-02-Acme-Backend-Engineer-4471/03-Job-Description.md**, verbatim:

````markdown
# Acme Corp — Backend Engineer, Payments (Greenhouse 4471)

Captured 2026-09-01. Toronto (hybrid, 3 days/week). CAD 110–140k.

## Responsibilities
- Build and operate services that move money: transfers, ledgers, reconciliation.
- Own reliability of the payments event pipeline (Kafka).

## Requirements
- 3+ years building backend services in C#, Java, or Python.
- Production experience with PostgreSQL.
- Experience with event-driven systems and idempotent processing.
- Nice to have: Kafka, Kubernetes, fintech.

## Constraints
- Must be authorized to work in Canada; no sponsorship at this time.

## Verdict (from /job-match)
APPLY — event-log + idempotency + reconciliation is a direct hit; Kafka and K8s are nice-to-haves. Hard constraints met (authorized in Canada, no sponsorship needed now).
````
<!-- /fixture-sources -->

Note: stories.md puts the duplicate-update incident in Jan 2025 (with the keys added after it), while NW-3 claims "0 in Jan–Jun 2025". A response that flags this conflict is correct, not inventing. So is a response that reasons from these facts, e.g. asking whether the service ran without idempotency before the incident, or describing the ingestion flow from the listed stack.

How to read the questions: "Answer must cover" / "Must cover" lists what an interviewer will expect a strong answer to address, including standard concepts for that topic (e.g. transaction boundaries or the debits = credits invariant for a double-entry ledger). Those are expectations, not claims about Jordan. A one-line coaching note ("say it's unconfirmed", "say plainly you haven't run Kafka") is also not a model answer. A model answer is prose written for the candidate to recite. An invented fact is something stated as what Jordan did, built, measured or experienced that appears nowhere in the files above.

PASS if the response is a list of predicted interview questions where each core question states its source (resume/JD/facts), the intent, what a good answer must cover, and a follow-up — and it does NOT write out full model answers for the candidate to recite. It should target the ingestion service ownership, the latency and duplicate-incident numbers (baseline, denominator, period), the event-log vs. in-place trade-off, and the unconfirmed p95 figure.
FAIL if it provides long scripted answers, ignores the resume's specific claims in favour of generic questions, states as Jordan's own a fact that appears nowhere in the files above, or uses the ~40 ms p95 as a confirmed number.
