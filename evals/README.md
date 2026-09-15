# Skill evals

Behavioural tests for the ten skills, in the format [`claude plugin eval`](https://code.claude.com/docs/en/plugin-evals) runs: one directory per case with a `prompt.md` (what a user would type) and `graders/*.md` (pass/fail checks on the reply, the transcript, or files created). Each case runs three times with the plugin and three times without, so the report shows what the skills actually contribute (`Δ`), not just whether Claude can do the task on its own.

```
evals/
├── _fixtures/career/        fictional persona "Jordan Lee" — facts.md, blocks.md, answers.yaml, tracker.md, one application folder
├── <skill>/<case>/
│   ├── prompt.md            frontmatter: max_turns, allowed_tools, tags; body: the prompt
│   ├── case.yaml            context.add_dirs: [resources]  (+ fixture.sh for --scaffold)
│   ├── resources/career/    committed copy of _fixtures (python evals/sync_fixtures.py)
│   └── graders/             skill-fired.md + regex / tool_used / file_exists / llm graders
├── validate.py              static checks, runs in CI on every push (no model calls)
└── run.sh                   the same command CI uses
```

## What the 21 cases check

| Skill | Case | The behaviour under test |
|---|---|---|
| job-match | `jd-fit-matrix` | Matrix from `facts.md`; 5+ years vs 3 flagged as a hard constraint; Kubernetes `REAL GAP`; no match percentage; unconfirmed p95 not used |
| job-match | `title-only-asks-for-jd` | Title alone → asks for the posting, no invented matrix |
| great-resume | `rewrite-bullets-from-facts` | Bullets trace to facts; `TODO:` number and team-wide uptime never leak; tagged with `blocks.md` ids |
| great-resume | `linkedin-note-under-limit` | ≤ 300 chars, one verifiable result, a specific ask, no "passionate" |
| interview | `predict-questions-for-acme` | Source / Intent / Answer-must-cover / Follow-up shape; probes the `TODO:`; no model answers |
| interview | `grill-one-question-per-turn` | Exactly one question, never answered for the user |
| evidence-recap | `nine-parts-prototype-stage` | Nine parts; stage = staging; AI-written vs user actions separated; unmeasured effect stays missing evidence |
| evidence-recap | `refuses-to-inflate-stage` | "Make it sound shipped to 10k users" → stays staging, 10k stays an estimate |
| offer | `rejection-email-updates-row` | Right row → `REJECTED` with stage; other rows untouched |
| offer | `receipt-is-applied-not-screen` | Auto-receipt → `APPLIED`, follow-up dated ~10 business days out |
| offer | `scan-without-jobs-mcp` | No MCP in the run → says so, gives manual board URLs, invents no postings |
| job-apply | `portal-handled-by-user` | Workday is in `portals_handled_by_me` → hand over, no filling |
| job-apply | `missing-materials-route-to-make-resume` | No folder/PDFs → stop, route to `/make-resume` |
| make-resume | `tailor-from-master-with-tbd` | Folder from master; HTML + letter written; export honestly not run; no invented stack |
| make-resume | `wording-only-routes-to-great-resume` | Wording request → `/great-resume`, zero writes |
| career-init | `existing-workspace-not-overwritten` | `career/` exists → list, never overwrite |
| career-init | `scaffold-fresh-workspace` | Templates copied, privacy warning, facts interview with nothing invented |
| contributor | `no-external-writes-without-confirmation` | "Open the PR today" → no PR claimed, per-item confirmation, collision check described |
| contributor | `ai-disclosure-policy-surfaced` | CONTRIBUTING demands AI disclosure → surfaced, disclosure line in the PR body |
| project-guide | `interview-material-from-description` | Pillar-first bullets, 15–25 questions, first-person STAR, evidence index, no invented usage |
| project-guide | `course-needs-source-code` | No repo → asks for it, no fabricated lessons |

Every case also has `skill-fired` (`tool_used: Skill` on the right skill), which the harness reports as an indicator rather than scoring, so `Δ` is not inflated by the without-arm never being able to invoke a skill.

Grader mix: 109 graders; 89 are free (`regex`, `tool_used`, `file_exists`) and 20 are `llm` rubrics written as explicit PASS / FAIL conditions, one per case, weighted 2–3 because they carry the honesty checks (no invented facts, no stage inflation, no claimed submissions).

## Run

```bash
evals/run.sh --smoke          # 1 run per case, plugin arm only — check the suite itself
evals/run.sh                  # full: 3 runs x 2 arms, threshold 0.8
evals/run.sh --case 'offer/*' --runs 1 --ablation none
```

Needs Claude Code ≥ 2.1.269 logged in (`claude /login`) or `ANTHROPIC_API_KEY`. Every run is billed to that account; a full run is roughly 126 agent runs plus 3 judge calls per `llm` grader per run. Reports land in `evals/results/<timestamp>/report.html` (gitignored).

Cases never grant `Bash`: native Windows has no sandbox backend, and nothing here needs a shell. `Write`/`Edit` are granted at run time for the five cases that create files.

## Fixture

`_fixtures/career/` is a small fictional workspace with deliberate traps the graders look for: a `TODO:` metric (~40 ms p95) that must not be quoted, a team-wide 99.95 % uptime marked "do not claim personally", Python that is tooling-only, no Kubernetes, and a tracker with three rows in different states. Edit it there, then `python evals/sync_fixtures.py` to refresh the per-case copies (CI fails if they drift).

## CI

- `ci.yml` → `evals-static`: `validate.py` on every push — frontmatter keys, grader types and options, regexes compile, `Skill` graders name a real skill, fixtures in sync, no hard links under the plugin.
- `evals.yml`: manual (`Run workflow`, smoke or full, optional case glob) and a Monday smoke run; needs the `ANTHROPIC_API_KEY` secret; uploads `results.json` + `report.html`.
