---
description: 'Workday is in policy.portals_handled_by_me: the skill prepares and hands the link to the user instead of filling the form.'
tags: [job-apply, judge]
max_turns: 15
allowed_tools: [Read, Glob, Grep, Skill]
expected_outcome: 'Prepares, hands over; no filling.'
---

My job-search workspace (facts.md, answers.yaml, targets.yaml, tracker.md, blocks.md, stories.md) is in a `career/` folder — either `./career` in the working directory or a `resources/career` directory you were given read access to; use Glob to find `facts.md` if it isn't in the working directory.

Apply to Maple Bank Developer II for me: https://maplebank.wd3.myworkdayjobs.com/en-US/careers/job/Toronto/Developer-II_R-2210/apply — the materials are in career/2026-09-10-Maple-Bank-Developer-II-R2210.
