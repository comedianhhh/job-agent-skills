---
type: 'llm'
weight: 3
---

The candidate (Jordan Lee) asked for ONE ~45-second spoken "tell me about yourself" for an Acme payments backend call with Priya, whose post was about duplicate webhooks, retries landing twice, and state nobody can rebuild. Jordan's real material: at Northwind Logistics (current job) Jordan owned a shipment-events ingestion service — carrier webhooks deduplicated by idempotency key, an append-only event log in PostgreSQL, and a reconciliation job that re-derives state from the log; duplicate-update incidents went from 3–4 per month to 0 over six months; carrier-update latency went from ~15 minutes to under 30 seconds. Earlier: a Unity/Node co-op at Blue Maple Games, a BASc at Waterloo, and a personal ledger project (ledger-lite).

PASS if all hold:
1. The reply gives one finished intro script (it may add a short beat outline or one or two practice notes, but not two or more alternative versions to choose from).
2. The idempotency / duplicates / reconciliation / event-log story is the first story the script tells (one short opening line naming Jordan's current role is fine) and it carries at least one of its real numbers (3–4 a month → 0, or ~15 minutes → under 30 seconds).
3. The rest of the background (co-op, school, ledger-lite) takes at most about two sentences.
4. The script ties back to Priya's post (duplicates, retries, or rebuilding state) near the end, either by naming it or by plainly answering it.

FAIL if the script walks through Jordan's history in time order (school → Blue Maple → Northwind, or "I started at…, then…"), opens with education or a generic line about being passionate, offers multiple versions, or states inside the script the unconfirmed ~40 ms p95 latency or the team-wide 99.95% uptime as Jordan's result. Notes outside the script that say these were left out are fine.
