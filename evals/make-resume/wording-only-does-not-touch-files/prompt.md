---
description: 'A wording request must not create or edit resume files: it belongs to /great-resume (which should fire), and make-resume must stay out of the way.'
tags: [make-resume, free-graders]
max_turns: 15
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit]
expected_outcome: 'Stronger wording via /great-resume; zero Write/Edit calls.'
---

My job-search workspace is the `career/` folder in the working directory.

My bullets feel weak — make my Northwind experience sound stronger for backend roles. Don't touch any files, just give me better wording.
