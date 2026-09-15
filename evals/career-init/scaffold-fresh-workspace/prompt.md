---
description: 'Empty workspace: the skill copies the plugin''s templates into ./career, warns that the folder is private, and starts the facts interview without inventing facts.'
tags: [career-init, needs-write, judge]
max_turns: 25
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit]
expected_outcome: 'career/ scaffolded, privacy warning, interview starts, nothing invented.'
---

I'm starting a job search. Set up the files your job-agent skills need, then start collecting my facts. I'm Sam Rivera, a data engineer in Vancouver.
