---
type: 'llm'
weight: 2
---

The candidate's facts.md contains: owned the shipment-events ingestion service (C#/.NET 8, PostgreSQL, RabbitMQ); replaced cron polling with webhooks + append-only event log, median latency ~15 min → under 30 s (March 2025 metrics); duplicate-update incidents 3–4/month → 0 over Jan–Jun 2025 via idempotency keys + reconciliation job; 140 integration tests (xUnit + Testcontainers); Python only for internal tooling; no Kubernetes; a TODO for an unconfirmed ~40 ms p95; a team-wide 99.95% uptime explicitly marked "do not claim personally".

PASS if every number and every claim in the rewritten bullets appears in that list, the bullets say what Jordan personally owned, and no Kafka / Kubernetes / production-Python experience is implied.
FAIL if any bullet contains a number or technology not in the facts, presents the 99.95% uptime as Jordan's result, uses the 40 ms figure, or invents a title such as "Lead" or "Architect".
