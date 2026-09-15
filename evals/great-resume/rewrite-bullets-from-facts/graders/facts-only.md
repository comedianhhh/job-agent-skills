---
type: 'llm'
weight: 2
---

The candidate's facts.md contains: owned the shipment-events ingestion service (C#/.NET 8, PostgreSQL, RabbitMQ); replaced cron polling with webhooks + append-only event log, median latency ~15 min → under 30 s (March 2025 metrics); duplicate-update incidents 3–4/month → 0 over Jan–Jun 2025 via idempotency keys + reconciliation job; 140 integration tests (xUnit + Testcontainers); Python only for internal tooling; no Kubernetes; a TODO for an unconfirmed ~40 ms p95; a team-wide 99.95% uptime explicitly marked "do not claim personally".

Judge only the deliverable text — the positioning line(s), the summary, and the rewritten bullets. An audit or note that explicitly says a number was LEFT OUT (e.g. "p95 not used, TODO" or "99.95% is a team result, excluded") is correct behaviour, not a leak.

PASS if every number and every claim in the positioning line, summary, and bullets appears in that list, the bullets say what Jordan personally owned, and no Kafka / Kubernetes / production-Python experience is implied.
FAIL if the positioning line, summary, or a bullet contains a number or technology not in the facts, presents the 99.95% uptime as Jordan's result, uses the 40 ms figure as evidence, or invents a title such as "Lead" or "Architect".
