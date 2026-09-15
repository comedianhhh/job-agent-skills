---
description: 'An automatic application-received email must map to APPLIED, never SCREEN, and the next step must carry a follow-up date.'
tags: [offer, judge]
max_turns: 15
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit]
expected_outcome: 'New row, APPLIED, follow-up ~2026-09-29.'
---

My job-search workspace (facts.md, answers.yaml, targets.yaml, tracker.md, blocks.md, stories.md) is in a `career/` folder — either `./career` in the working directory or a `resources/career` directory you were given read access to; use Glob to find `facts.md` if it isn't in the working directory.

New email from Orbital Freight: "Thanks for applying to Senior Backend Engineer — Platform (req OF-118). We've received your application and our team will review it." I applied today, 2026-09-15, through their Greenhouse page. Add it to the tracker.
