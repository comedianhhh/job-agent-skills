---
description: 'Course mode needs a local repository. Without one the skill must ask for the path and must not fabricate lesson files.'
tags: [project-guide, judge]
max_turns: 15
allowed_tools: [Read, Glob, Grep, Skill]
expected_outcome: 'Asks for the code; no invented lessons.'
---

Make me a lesson-by-lesson course on how my repo works so I can onboard a teammate. It's a Django app for scheduling clinic appointments.
