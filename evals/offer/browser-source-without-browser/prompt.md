---
description: 'targets.yaml lists a Wellfound browser source, but the run has no browser tool and no jobs-mcp. The skill says browser sources are searched in the user's own signed-in browser; without one it must say so, not invent Wellfound postings.'
tags: [offer, judge]
max_turns: 15
allowed_tools: [Read, Glob, Grep, Skill]
expected_outcome: 'Says the Wellfound search needs the browser and jobs-mcp is missing; no invented postings.'
---

My job-search workspace is the `career/` folder in the working directory.

Scan everything in my targets for new postings, including Wellfound.
