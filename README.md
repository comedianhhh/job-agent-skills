# job-agent-skills

[![CI](https://github.com/comedianhhh/job-agent-skills/actions/workflows/ci.yml/badge.svg)](https://github.com/comedianhhh/job-agent-skills/actions/workflows/ci.yml) [![npm](https://img.shields.io/npm/v/job-agent-skills)](https://www.npmjs.com/package/job-agent-skills)

A job-search workflow for coding agents, built for the US and Canadian market. Ten skills for Claude Code and [pi](https://github.com/earendil-works/pi) (and any agent that reads `SKILL.md`) plus **jobs-mcp**, an MCP server that scans Greenhouse, Lever, Ashby, SmartRecruiters and LinkedIn for new postings.

It is built around one rule: **every line that goes out traces to a fact you wrote down.** The agent tailors, formats, fills forms, tracks, and drills you for interviews — it never invents a title, a number, or an ownership claim.


## What you get

**Apply track**

| Skill | Does |
|---|---|
| `/career-init` | Scaffolds your private `career/` workspace and interviews you for `facts.md` and `answers.yaml`. |
| `/job-match` | JD → posting-integrity verdict, requirement–evidence matrix, hard constraints (work authorization, location, years, band), your own interview-rate signals, `APPLY` / `SKIP`. |
| `/great-resume` | Positioning, summary, bullet rewrites, LinkedIn note / cold email / referral ask. |
| `/make-resume` | One-page Letter resume + cover letter for one role. A second agent (`application-reviewer`) critiques the drafts as the hiring manager before export; then three deterministic gates: every number traceable to `facts.md` (`check-trace.py`), one page (overflow cut by relevance with `rank-cuts.py`, not by age), and the PDF's text layer read the way an ATS reads it (`check-ats.py`). |
| `/job-apply` | Fills the application in your browser from `answers.yaml`, stops before Submit (or not — your policy), records it. |
| `/offer` | Pipeline in `tracker.md`; mailbox triage; daily scan of your target boards via jobs-mcp; regenerates `calibration.md` when outcomes land. |
| `/interview` | Predict → grill (one question at a time, scoring contracts) → review → retry. NA round structure. |

**Build track**

| Skill | Does |
|---|---|
| `/contributor` | Finds real, unclaimed issues in maintained repos, prepares a verified diff, and only after per-item confirmation forks / pushes / opens the PR. |
| `/project-guide` | Turns a repo into a lesson-by-lesson course, or your project into `guide-` + `interview-` files (pillar bullets, 15–25 questions, STAR answers). |
| `/evidence-recap` | Turns an AI coding session into a nine-part evidence chain; confirmed facts flow into `facts.md`. |

**jobs-mcp** — `list_board_jobs`, `get_job`, `linkedin_search`, `scan`. No API keys; these are the public endpoints the career pages use. `scan(rank_query=...)` ranks postings against your profile with BM25, plus local embeddings fused by RRF when the optional `rank` extra is installed. Every fetched description goes through the posting guard first (`jobs_mcp/guard.py`): hidden HTML and invisible Unicode are removed, text spelled in tag characters or variation selectors is decoded, instruction-shaped lines are quoted, and the result is attached as `integrity`. Plain tag stripping would have turned hidden text into visible text for the model.

**Evals** (`evals/`) — 22 `claude plugin eval` cases, two per skill plus a prompt-injection case, that check the behaviours that matter (facts never invented, stage never inflated, nothing submitted without confirmation, JD text never obeyed) against a no-plugin baseline. See [evals/README.md](evals/README.md).

**Tracker web app** (`web/`) — a kanban over the same `career/tracker.md` the skills write, plus a scan page that runs jobs-mcp against `targets.yaml`. Next.js + FastAPI + Postgres, `docker compose up`. See [web/README.md](web/README.md).

## Install

### As a Claude Code plugin

```bash
claude plugin marketplace add comedianhhh/job-agent-skills
claude plugin install job-agent-skills
```

jobs-mcp starts through `uvx` (install [uv](https://docs.astral.sh/uv/) if you do not have it).

### As a pi package

```bash
pi install npm:job-agent-skills
# or straight from git:
pi install git:github.com/comedianhhh/job-agent-skills
```

Skills load as `/skill:job-match`, `/skill:offer`, … (or the model picks them up on its own). pi has no MCP support by design, so the bundled extension ([extensions/jobs-mcp.ts](extensions/jobs-mcp.ts)) starts jobs-mcp over stdio at session start and registers its four tools natively — `list_board_jobs`, `get_job`, `linkedin_search`, `scan`. It needs `uv` on PATH; set `JOBS_MCP_COMMAND=jobs-mcp` to use a `pip install -e mcp/jobs-mcp` install instead. If the server cannot start, pi shows a warning and the skills still load.

### Manual

Copy `skills/*` into `.claude/skills/` of any project (or `~/.claude/skills/`), and add jobs-mcp to your MCP config:

```json
{ "mcpServers": { "jobs-mcp": { "command": "uvx", "args": ["--from", "/path/to/job-agent-skills/mcp/jobs-mcp", "jobs-mcp"] } } }
```

or `pip install -e mcp/jobs-mcp` and use `"command": "jobs-mcp"`.

## Quick start

```text
/career-init                       # creates career/, walks you through facts.md and answers.yaml
/job-match <paste a JD or link>    # worth applying? what are the gaps?
/make-resume                       # tailor + export PDFs for that role
/job-apply <application URL>       # fill the form from your standing answers
/offer                             # record it; later: "scan for new jobs"
/interview grill                   # when a screen lands
```

Typical day: `/offer scan` in the morning → `/job-match` on anything promising → `/make-resume` → `/job-apply` → `/offer`. Evenings: `/contributor` or a project, then `/evidence-recap` so the work becomes resume evidence.

## Tracker web app

```bash
cp .env.example .env    # TRACKER_TOKEN + CAREER_DIR
docker compose up -d    # http://localhost:3000 — paste the token once
```

Drag a card between columns and the status cell of that one row in `tracker.md` changes — nothing else in the file is touched. "Scan now" calls jobs-mcp with your `targets.yaml`, marks postings already in the tracker, appends the rest to `career/SCAN-<date>.md` (the same table `/offer` writes), and "track" turns a posting into a `DRAFT` row for `/job-match` to pick up. Postgres only holds what markdown shouldn't: status-change history (for the 10-business-day follow-up flag) and scan history. Details and the no-Docker dev setup are in [web/README.md](web/README.md).

## The `career/` workspace

Private. Keep it out of public repos (`.gitignore` here already excludes it).

| File | Purpose |
|---|---|
| `facts.md` | Single source of truth — every other file is derived from it. `TODO:` marks what you have not confirmed; those never go out. |
| `blocks.md` | Finished bullets — resumes are assembled, not rewritten. |
| `stories.md` | STAR stories by question type, `[fact]` vs `[draft — confirm]`. |
| `rules.md` | Your resume standard. |
| `answers.yaml` | Standing form answers and your submit policy. |
| `targets.yaml` | Boards and filters for scanning. |
| `tracker.md` | The pipeline. |
| `application/` | Template for each role folder: resume, letter, JD analysis, interview prep. |

See `templates/career/README.md`.

## Design notes

- **Facts before prose.** `job-match` refuses to score on keywords; `great-resume` refuses to add facts; `interview` treats the resume as claims to be defended.
- **Deterministic where it can be.** The model is told to trace every claim; `scripts/check-trace.py` checks the part a script can check (numbers and leftover markers) before any PDF is produced. `scripts/career-eval.py` turns your own sent folders and tracker into offline evals: block-selection recall against a BM25 baseline, and interview rates with Wilson intervals; `calibrate` writes `career/calibration.md`, which marks only the groups (source, track, seniority, tailoring, stretch) that differ from the rest beyond noise, and `/job-match` may cite only those. `scripts/posting-guard.py` runs the jobs-mcp guard on pasted postings; `scripts/check-ats.py` extracts the exported PDF's text (pypdf or pdftotext) and fails on missing contact text or bullets spliced by a multi-column layout; `scripts/rank-cuts.py` orders bullets for cutting by relevance, uniqueness, and cover-letter dependency.
- **A second reader.** The drafter does not grade its own draft: `agents/application-reviewer.md` reviews it in a fresh context, read-only, and returns `old`/`new` edits each tied to a `facts.md` section; the drafter checks every source before applying one.
- **External writes are confirmed.** Submitting an application, opening a PR, sending a message — each is shown and confirmed unless your `answers.yaml` policy says otherwise.
- **NA specifics.** Letter paper, one page, no photo or personal-data block; hard constraints are work authorization / sponsorship / location / years / band; pipeline is APPLIED → SCREEN → OA → TECH → ONSITE → OFFER; outreach is LinkedIn notes and cold email, not chat openers.
- **No agent framework.** Skills are Markdown; the MCP server is ~300 lines of Python on `httpx`.
- **One skill set, two hosts.** The same `skills/` load as a Claude Code plugin and as a pi package; the pi extension (~100 lines, `@modelcontextprotocol/sdk`) is the only host-specific code. `npm run check` type-checks it, `npm run test:pi` loads it against a fake `ExtensionAPI` and round-trips a `scan` call.


## Releasing

```bash
npm run verify           # ~30 s while working
npm run verify:release   # ~10 min before publishing (adds the skill evals)
```

Both check exactly what `npm publish` would ship. They run the offline checks CI runs, pack the tarball (required files present, nothing private), start jobs-mcp from the packed copy, and call live Greenhouse, Lever, Ashby, SmartRecruiters and LinkedIn. `verify:release` also runs the skill evals in smoke mode through the logged-in `claude` CLI. Only deterministic graders gate the verdict; llm-judge results are reported as notes. The verdict is PASS, FAIL, or BLOCKED (something couldn't be checked, e.g. a board was unreachable). Evidence goes to `.verify/<run>/`. A `verify:release` PASS prints the tarball to publish: `npm publish .verify/<run>/<file>.tgz`. See `.claude/skills/verify-release/SKILL.md`.

## License

MIT — see [LICENSE](LICENSE).
