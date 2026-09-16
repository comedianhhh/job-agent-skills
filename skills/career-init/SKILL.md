---
name: career-init
description: Scaffold the private career/ workspace that every other job-agent skill reads — facts.md (single source of truth), blocks.md, stories.md, rules.md, answers.yaml (standing form answers), targets.yaml (boards to scan), tracker.md, and the per-application template. Use when the user types /career-init, asks to set up job-search files, or when another skill finds no career/ folder.
---

# /career-init — Set up the workspace

Create `career/` in the current project (or the path the user gives) from this plugin's `templates/career/` (the `templates/` folder sits next to `skills/` in the install root), then walk the user through the two files that everything depends on.

## Steps

1. If `career/` already exists, stop and list what is there — never overwrite.
2. Copy `templates/career/` → `career/`. Say plainly: **this folder is private**; suggest adding it to a private repo or `.gitignore`.
3. Fill `career/facts.md` interactively, one section at a time: basics, work authorization, education, each job (title, stack, dates, verifiable anchors, then facts with numbers). Write `TODO:` where the user is unsure. Do not polish wording here — this file is facts, not prose.
4. Fill `career/answers.yaml`: identity, authorization (sponsorship yes/no now and in future), years of experience (default and excluding internships), work model, salary floor, EEO choices (blank = prefer not to say), and the policy block (`submit_without_confirmation`, portals the user handles themselves, max roles per company).
5. Point `career/targets.yaml` at the boards the user cares about (`greenhouse:<token>`, `lever:<company>`, `ashby:<org>`) and one or two LinkedIn queries.
6. Finish with the sequence: `/job-match → /make-resume → /job-apply → /offer`, then `/interview` when a screen lands; `/great-resume` to strengthen bullets; `/contributor`, `/project-guide`, `/evidence-recap` for the build track.

## Rules

- Never invent facts to fill gaps; leave `TODO:`.
- Do not paste the user's phone number, email, or answers into any public file or chat log beyond what they typed.
- If `jobs-mcp` is not configured, tell the user how (see the README: MCP config for Claude Code; in pi the bundled extension starts it, which needs `uv` on PATH) — `/offer` scanning needs it.
