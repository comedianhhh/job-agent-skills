---
name: contributor
description: Find, prepare, and submit real open-source contributions that match the target roles — discover maintained repos, find genuine unclaimed issues, check for duplicate PRs, prepare a minimal verified change on a dedicated branch, and only after per-item confirmation fork, push, open the PR, and track CI / review / merge. Use when the user types /contributor, wants a first contribution, a PR candidate list, or a recurring contribution routine.
---

# /contributor — Real open-source contributions

`find a fitting repo → find a real issue → prepare the minimal change → verify locally → submit after confirmation → track the result`

Start with clearly scoped, verifiable changes (docs, dead links, examples, tests, small bugs) and go deeper as the repo's rules and your verification allow. A typo PR is a foot in the door, not a resume line; what reaches the resume is decided by `/great-resume` under `career/rules.md`.

## Modes

Ask for the target roles and GitHub account only if unknown (targets are in `career/tracker.md`; stack in `career/facts.md`).

- **Quick start** — typos, Markdown, dead links, README fixes.
- **Role-matched** — repos owned by target companies and the stacks their JDs name; tests, examples, small bugs.
- **Progressive (default)** — one scoped fix first, then a role-relevant, verifiable feature or test change.

Prefer mid-size, active repos over famous ones: "good first issue" on a 50k-star repo usually has several open PRs already.

## Workflow

1. **Discover (read-only).** Repos matching the role/stack with recent maintenance and external contributions allowed; check `CONTRIBUTING`, license, default-branch activity, issue/PR flow. No fork, no push.
2. **Find a real issue.** Genuine, scoped, locally verifiable. **Collision check is mandatory and authoritative:** the issue's linked PRs (`gh api repos/<o>/<r>/issues/<n>/timeline`) and the open-PR title list (`gh pr list --state open`); keyword search is supplementary. Someone already claimed it in comments or opened a PR → drop or downgrade. Record issue age, last update, assignees, claims, related PRs.
3. **Read the rules.** `CONTRIBUTING`, `AGENTS.md`, `AI_POLICY.md`, PR template. Forbidden PR type → `ineligible`, drop. Requires claim / approval / issue-first → `blocked`, no branch until met. **If the repo requires AI-assistance disclosure, tell the user before the PR is written — never omit it silently.**
4. **Prepare locally.** Dedicated branch from the current upstream baseline (the branch `CONTRIBUTING` names — often not `main`); never stack on an existing PR branch. Minimal change. Run the verification the repo's CI config implies (tests, lint, build, link check); record results. Show the **full diff**.
5. **External writes one by one.** Fork, push, open PR, comment, resolve thread, re-request review — each listed with repo, account, branch, files, exact action, and (for a PR) the complete title, body, diff. Wait for an explicit yes per item. "Find N" / "just do it" authorise candidates and local diffs, not writes. A confirmation covers one repo, one run.
6. **One confirmed PR at a time.** Track CI / review / merge read-only; on failure, separate code vs. config vs. environment and draft the minimal fix, then back to step 5. Work on the **existing** PR branch for review feedback. Never report "done" while required checks are pending. Merged → `/great-resume`; unmerged → "submitted / in collaboration", never "adopted".

Rank candidates by fit, genuineness, policy, collision risk, scope, verifiability, and what the user learns. No candidate to make up numbers.

## Commit and PR hygiene

- Commits are authored by the user only; no co-author lines for AI tools unless the repo's policy asks for disclosure and the user agrees.
- PR body follows the repo template, **kept short**: one or two sentences per section, verification as bullets (versions, what passed, what failed and why), alternatives in one sentence.
- One PR solves one problem; title and body in the repo's language; no boilerplate across repos.

## Routine mode

For daily/weekly runs the host scheduler invokes this skill; it never runs timers itself. Each run: read-only status of existing PRs → rotate candidates across targets → ≤ 2 verified candidates with diffs → per-item confirmation → daily report (status, candidates checked, PRs prepared/submitted, verification, drops). Zero candidates is a normal result. Setup: [references/daily-routine.md](references/daily-routine.md).

## After merge → `/great-resume`

Per PR: repo, link, merge date; problem and actual change; language, tools, verification; review/CI; countable results. Hand-off prompt:

> Use /great-resume to turn the contribution record below into a project entry, 2–3 bullets, and a recruiter note for **<target role>** — strictly from the actual change, personal boundary, verification, real PR links, and current merge status. Never write an unmerged PR as adopted.

Add the fact to `career/facts.md` (raw change, PR link, review/CI/merge status, scope boundary) with the user's confirmation; unmerged stays `TODO:`.

GitHub's displayed status is the truth. "Merged" is not "adopted by the project" unless the project says so.
