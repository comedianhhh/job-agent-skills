---
description: 'Guide + interview mode from a project description: pillar-first bullets, 15–25 questions with first-person STAR answers, evidence index, no invented metrics.'
tags: [project-guide, judge]
max_turns: 25
allowed_tools: [Read, Glob, Grep, Skill]
expected_outcome: 'Pillar bullets + 15–25 questions + STAR answers + evidence index; no invented metrics.'
---

Turn my personal project into interview prep. ledger-lite: a FastAPI + PostgreSQL double-entry ledger I built alone in 2025. POST /transfers is idempotent via an Idempotency-Key header backed by a unique constraint; postings are append-only and balances are projections; transfers move through an explicit state machine initiated → submitted → settled / returned, and illegal transitions are rejected with the rule that blocked them; a reconciliation task compares projected balances with the sum of postings. 1,200 lines of Python, 60 pytest tests, CI on GitHub Actions. Nobody uses it but me. Target role: backend / payments. Slug: ledger-lite. Write the files if you can; otherwise give me the content in labelled Markdown blocks.
