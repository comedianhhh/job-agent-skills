---
description: 'jobs-mcp is not available in the run. The skill says: say so and give the manual board URLs from targets.yaml — not pretend to scan.'
tags: [offer, judge]
max_turns: 15
allowed_tools: [Read, Glob, Grep, Skill]
expected_outcome: 'Explains jobs-mcp is missing; manual URLs; no invented postings.'
---

My job-search workspace (facts.md, answers.yaml, targets.yaml, tracker.md, blocks.md, stories.md) is in a `career/` folder — either `./career` in the working directory or a `resources/career` directory you were given read access to; use Glob to find `facts.md` if it isn't in the working directory.

Scan my target boards for new postings from the last 24 hours.
