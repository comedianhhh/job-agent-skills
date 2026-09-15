---
description: 'A rejection email for a tracked application. Expected: the Acme row moves to REJECTED with the stage noted, reported as before → after.'
tags: [offer, judge]
max_turns: 15
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit]
expected_outcome: 'Acme row APPLIED → REJECTED (stage: after application); others untouched.'
---

My job-search workspace is the `career/` folder in the working directory.

Just got this from Acme:

"Hi Jordan, thank you for taking the time to apply to the Backend Engineer, Payments position. After careful consideration we have decided not to move forward with your application at this time. We'll keep your profile on file. — Acme Talent Team"

Update my pipeline. (If you can't edit the file, show me the exact row change.)
