# ledger-lite

Double-entry ledger API (FastAPI + PostgreSQL). Idempotent `POST /transfers`, append-only postings.

## Settlement events

Every settled posting is published to the Kafka topic `ledger.postings.settled` (see `worker/`).
A consumer group (`worker/settlement_consumer.py`) applies them to the balance read model and
commits offsets only after the database write, so a crash replays the event instead of losing it.
Run it locally with `docker compose up kafka worker`.
