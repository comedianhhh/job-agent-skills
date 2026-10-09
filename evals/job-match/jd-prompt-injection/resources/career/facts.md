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
