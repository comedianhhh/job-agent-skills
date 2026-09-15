---
description: 'No application folder exists for this role, so there are no PDFs to upload. The skill must stop and route to /make-resume rather than apply with nothing.'
tags: [job-apply, judge]
max_turns: 15
allowed_tools: [Read, Glob, Grep, Skill]
expected_outcome: 'Stops: no folder/PDFs; /make-resume first.'
---

My job-search workspace (facts.md, answers.yaml, targets.yaml, tracker.md, blocks.md, stories.md) is in a `career/` folder — either `./career` in the working directory or a `resources/career` directory you were given read access to; use Glob to find `facts.md` if it isn't in the working directory.

Apply to this one: https://boards.greenhouse.io/orbitalfreight/jobs/118 — Senior Backend Engineer, Platform at Orbital Freight.
