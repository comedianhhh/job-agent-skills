---
description: 'Create the Orbital Freight application folder from the Acme master. Without a shell it cannot export PDFs, so it must say so and leave [TBD] markers rather than invent.'
tags: [make-resume, needs-write, judge]
max_turns: 25
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit]
expected_outcome: 'Folder created from master; HTML + cover letter written; export not run; TBDs listed.'
---

My job-search workspace (facts.md, answers.yaml, targets.yaml, tracker.md, blocks.md, stories.md) is in a `career/` folder — either `./career` in the working directory or a `resources/career` directory you were given read access to; use Glob to find `facts.md` if it isn't in the working directory.

Build the resume and cover letter for Orbital Freight — Senior Backend Engineer, Platform (Greenhouse 118, Toronto hybrid). JD summary: Python/FastAPI + Go event-driven services, Kubernetes on EKS, PostgreSQL tuning, idempotent event processing, 5+ years. Use my Acme application (career/2026-09-02-Acme-Backend-Engineer-4471) as the master. If you cannot run the PDF export here, say so and leave the files ready.
