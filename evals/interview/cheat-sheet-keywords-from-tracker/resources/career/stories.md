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
