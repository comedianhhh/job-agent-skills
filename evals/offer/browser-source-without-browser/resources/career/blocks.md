# Blocks — finished, copy-ready bullets (fictional eval persona)

## Northwind — ingestion
- **NW-1** Owned the shipment-events ingestion service end to end (C#/.NET 8, PostgreSQL, RabbitMQ): carrier webhooks → idempotent append-only event log → projected shipment state; on-call for it since launch (Nov 2024).
- **NW-2** Replaced cron polling with webhook ingestion + event log, cutting median carrier-update-to-dashboard latency from ~15 min to <30 s across all shipment updates (Mar 2025 production metrics).
- **NW-3** Eliminated duplicate-update incidents (3–4/month in Q4 2024 → 0 in Jan–Jun 2025) with idempotency keys and a reconciliation job that re-derives state from the log.
- **NW-4** Built the service's integration suite (xUnit + Testcontainers, 140 tests) running on every PR in GitHub Actions.

## Projects
- **LL-1** ledger-lite (personal): FastAPI + PostgreSQL double-entry ledger with idempotent transfers, append-only postings, and an explicit transfer state machine; 60 pytest tests, CI on GitHub Actions.
