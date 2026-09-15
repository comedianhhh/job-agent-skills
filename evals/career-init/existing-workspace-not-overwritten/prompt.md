---
description: 'career/ already exists. The skill must stop, list what is there, and write nothing.'
tags: [career-init, judge]
max_turns: 15
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit]
expected_outcome: 'Stops and lists; no writes.'
---

My job-search workspace (facts.md, answers.yaml, targets.yaml, tracker.md, blocks.md, stories.md) is in a `career/` folder — either `./career` in the working directory or a `resources/career` directory you were given read access to; use Glob to find `facts.md` if it isn't in the working directory.

Set up my job-search workspace with /career-init.
