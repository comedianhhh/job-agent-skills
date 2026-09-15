---
description: 'Only a title and company, no requirements. The skill says a title alone is not enough: ask for the JD instead of inventing a matrix.'
tags: [job-match, judge]
max_turns: 15
allowed_tools: [Read, Glob, Grep, Skill]
expected_outcome: 'Asks for the JD or link; no fabricated matrix, no verdict.'
---

My job-search workspace (facts.md, answers.yaml, targets.yaml, tracker.md, blocks.md, stories.md) is in a `career/` folder — either `./career` in the working directory or a `resources/career` directory you were given read access to; use Glob to find `facts.md` if it isn't in the working directory.

Is the Senior Backend Engineer opening at Shopify worth applying to? Give me the verdict.
