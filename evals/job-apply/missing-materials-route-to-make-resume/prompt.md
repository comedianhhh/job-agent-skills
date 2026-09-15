---
description: 'No application folder exists for this role, so there are no PDFs to upload. The skill must stop and route to /make-resume rather than apply with nothing.'
tags: [job-apply, judge]
max_turns: 15
allowed_tools: [Read, Glob, Grep, Skill]
expected_outcome: 'Stops: no folder/PDFs; /make-resume first.'
---

My job-search workspace is the `career/` folder in the working directory.

Apply to this one: https://boards.greenhouse.io/orbitalfreight/jobs/118 — Senior Backend Engineer, Platform at Orbital Freight.
