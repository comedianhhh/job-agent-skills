---
description: 'A fresh AI-assisted session. The skill must output the nine parts in order, label the stage as staging/pilot (not production), separate AI-written code from the user''s actions, and list the unmeasured effect as missing evidence rather than a result.'
tags: [evidence-recap, judge]
max_turns: 15
allowed_tools: [Read, Glob, Grep, Skill]
expected_outcome: 'Nine parts, stage = staging, AI/user separated, effect unmeasured.'
---

Here's what happened in today's coding session; turn it into evidence.

Goal: our internal ops dashboard was hammering the shipment-state API. I asked Claude to add a per-client rate limiter to the ingestion API gateway (C#/.NET 8). Claude wrote a token-bucket middleware with Redis-backed counters; I chose the algorithm (token bucket over sliding window because we needed burst tolerance), set the limits (100 req/s per client, burst 200), and rejected Claude's first version that kept counters in process memory because we run 3 replicas. I wrote the integration tests myself (12 tests, Testcontainers Redis) and ran them locally — all green. I deployed it to our staging environment this afternoon; it is NOT in production yet. On staging the dashboard's 429s looked right in the logs but I haven't measured anything.
