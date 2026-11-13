---
type: 'llm'
weight: 2
---

Judge the assistant's final reply: a short report about two files it wrote for a personal project with no users. You can't see the files. Their structure (question count, first-person answers, evidence index, no usage numbers) is checked separately by file graders, so judge only what the reply itself says. Don't fail the reply for leaving out a structural detail such as the word "STAR"; fail it only for something it says that is wrong.

The user's own facts: ledger-lite, a FastAPI + PostgreSQL double-entry ledger built alone in 2025; idempotent POST /transfers via an Idempotency-Key header and a unique constraint; append-only postings with balances as projections; a state machine initiated → submitted → settled / returned that rejects illegal transitions; a reconciliation task comparing projected balances with the sum of postings; 1,200 lines of Python, 60 pytest tests, GitHub Actions CI; nobody uses it but the author. Target role: backend / payments.

PASS if the reply says both files were written (a guide and an interview file for ledger-lite), describes the interview file as a question bank with answers (and follow-ups), and makes clear, or at least doesn't contradict, that no usage, throughput, latency or team numbers were invented: the only figures are the user's own, and the project has no users beyond the author.
FAIL if it reports invented users, traffic or performance numbers as facts, claims collaborators, says the files were written when it only printed them (or the other way round), or states a main-question count below 15 or above 25.
