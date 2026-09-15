---
name: job-match
description: Compare a job description against the verified facts in career/facts.md and return a requirement–evidence matrix, a hard-constraint check (work authorization, location, years, band), and an APPLY / SKIP verdict. Use when the user pastes a JD, a job link, or a screenshot and asks whether a role fits, is worth applying to, or what the gaps are. Hands off to /great-resume, /make-resume, /interview, /job-apply, /offer.
---

# /job-match — Requirement–evidence analysis

Break the JD into verifiable requirements and check each against evidence that already exists in `career/facts.md`. The output is not a match score; it is: which requirements have evidence, which are merely unwritten, which are real gaps, and whether the application is worth the time.

## Inputs

1. A concrete JD — text, link, or screenshot. A title alone is not enough; ask for the requirements. If `jobs-mcp` is available and the link is a Greenhouse / Lever / Ashby posting, fetch it with `get_job`.
2. `career/facts.md` (truth), `career/blocks.md` (wording), `career/stories.md` (depth). Never add a fact that is not there.
3. The user's filters in `career/targets.yaml` (`filters:`) and `career/answers.yaml` (`authorization`, `experience`, `preferences`).

Keep the capture date. If the JD is a fragment, say what is missing.

## Method

1. Extract responsibilities, hard requirements, core competencies, nice-to-haves, application constraints. Merge duplicates; ignore marketing copy.
2. For each requirement, find direct evidence and record **where** (`facts.md § …`) and the **personal boundary** (user vs. team).
3. One status each:
   - `MATCHED` — a specific, expandable fact exists.
   - `WORDING GAP` — the user did it; no resume version says it. Cheapest fix → `/great-resume`.
   - `THIN EVIDENCE` — hinted at; would not survive a follow-up.
   - `REAL GAP` — facts do not satisfy it, or the user confirmed they have not done it.
   - `UNCONFIRMED` — a decisive fact is missing; do not guess.
4. **Hard constraints first, separately; strengths never offset them.** Work authorization and sponsorship (from `answers.yaml`); country-restricted remote; onsite / hybrid vs. the user's work model; years required vs. `years_default` / `years_excluding_internships`; degree or certification; compensation vs. `salary_floor`; level (read the YOE range, not the title).
5. Verdict: `APPLY`, `APPLY AFTER PREP`, `APPLY WITH CAUTION`, `SKIP`, plus the two or three pieces of evidence that decided it. No percentages.
6. Name the resume master (which existing folder to copy) and which company-line anchors apply.

## Deliverable — same shape as `career/application/03-Job-Description.md`

1. **Verdict** — one sentence.
2. **Requirement–evidence matrix** — `| Requirement | Weight | Evidence (file § section) | Status | Risk / next step |`.
3. **Hard constraints** — met / not met / unconfirmed, each.
4. **Priority fixes** — ≤ 5, tagged `reword` / `add evidence` / `build skill`.
5. **Strategy** — apply or not, which master, open questions.
6. **Hand-off** — only if asked: the prompt for the next skill.

The evidence column must point at a section, project, artifact, PR, or explicit user statement. Nothing found → `not provided`.

## Boundaries

- Adjacent tech is not the same tech; say "transferable", keep the status honest.
- "Preferred / familiar with" is not a hard requirement unless the responsibilities say so.
- Do not reject on one missing keyword; do not accept on keyword overlap.
- Analysis authorises nothing else: no file edits, no forms, no submissions.
