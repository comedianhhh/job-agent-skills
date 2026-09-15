---
description: 'The user asks only for stronger wording, not files. make-resume must route to /great-resume instead of touching HTML.'
tags: [make-resume, free-graders]
max_turns: 15
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit]
expected_outcome: 'Routes to /great-resume; writes nothing.'
---

My job-search workspace (facts.md, answers.yaml, targets.yaml, tracker.md, blocks.md, stories.md) is in a `career/` folder — either `./career` in the working directory or a `resources/career` directory you were given read access to; use Glob to find `facts.md` if it isn't in the working directory.

My bullets feel weak — make my Northwind experience sound stronger for backend roles. Don't touch any files, just give me better wording.
