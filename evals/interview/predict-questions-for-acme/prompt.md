---
description: 'Predict-mode output has a fixed per-question shape (Source / Intent / Answer must cover / Follow-up) and must target the resume''s weakest-evidence claims, including facts.md TODOs.'
tags: [interview, judge]
max_turns: 15
allowed_tools: [Read, Glob, Grep, Skill]
expected_outcome: 'Ranked questions in the Source/Intent/Answer-must-cover/Follow-up shape; no model answers.'
---

My job-search workspace is the `career/` folder in the working directory.

Run interview prediction for my Acme Corp Backend Engineer, Payments application (the folder is career/2026-09-02-Acme-Backend-Engineer-4471, JD in 03-Job-Description.md). Hiring-manager technical round, 45 minutes. I want the high-probability questions, not model answers.
