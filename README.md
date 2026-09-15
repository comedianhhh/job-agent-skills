# job-agent-skills

[![CI](https://github.com/comedianhhh/job-agent-skills/actions/workflows/ci.yml/badge.svg)](https://github.com/comedianhhh/job-agent-skills/actions/workflows/ci.yml)

A job-search workflow for coding agents, **North American edition**. Ten skills for Claude Code (and any agent that reads `SKILL.md`) plus **jobs-mcp**, an MCP server that scans Greenhouse, Lever, Ashby and LinkedIn for new postings.

It is built around one rule: **every line that goes out traces to a fact you wrote down.** The agent tailors, formats, fills forms, tracks, and drills you for interviews — it never invents a title, a number, or an ownership claim.

Adapted from [ASu-skills](https://github.com/Hisn00w/ASu-skills) (MIT), which does this for the Chinese campus-recruiting market. This port keeps its structure — evidence matrix, interview contracts, claim taxonomy, per-item confirmation — and replaces everything market-specific with how hiring works in the US and Canada.

## What you get

**Apply track**

| Skill | Does |
|---|---|
| `/career-init` | Scaffolds your private `career/` workspace and interviews you for `facts.md` and `answers.yaml`. |
| `/job-match` | JD → requirement–evidence matrix, hard constraints (work authorization, location, years, band), `APPLY` / `SKIP`. |
| `/great-resume` | Positioning, summary, bullet rewrites, LinkedIn note / cold email / referral ask. |
| `/make-resume` | One-page Letter resume + cover letter for one role, exported to PDF with a one-page gate. |
| `/job-apply` | Fills the application in your browser from `answers.yaml`, stops before Submit (or not — your policy), records it. |
| `/offer` | Pipeline in `tracker.md`; mailbox triage; daily scan of your target boards via jobs-mcp. |
| `/interview` | Predict → grill (one question at a time, scoring contracts) → review → retry. NA round structure. |

**Build track**

| Skill | Does |
|---|---|
| `/contributor` | Finds real, unclaimed issues in maintained repos, prepares a verified diff, and only after per-item confirmation forks / pushes / opens the PR. |
| `/project-guide` | Turns a repo into a lesson-by-lesson course, or your project into `guide-` + `interview-` files (pillar bullets, 15–25 questions, STAR answers). |
| `/evidence-recap` | Turns an AI coding session into a nine-part evidence chain; confirmed facts flow into `facts.md`. |

**jobs-mcp** — `list_board_jobs`, `get_job`, `linkedin_search`, `scan`. No API keys; these are the public endpoints the career pages use.

**Tracker web app** (`web/`) — a kanban over the same `career/tracker.md` the skills write, plus a scan page that runs jobs-mcp against `targets.yaml`. Next.js + FastAPI + Postgres, `docker compose up`. See [web/README.md](web/README.md).

## Install

### As a Claude Code plugin

```bash
claude plugin marketplace add comedianhhh/job-agent-skills
claude plugin install job-agent-skills
```

jobs-mcp starts through `uvx` (install [uv](https://docs.astral.sh/uv/) if you do not have it).

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
| `facts.md` | Single source of truth. `TODO:` marks what you have not confirmed; those never go out. |
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
- **External writes are confirmed.** Submitting an application, opening a PR, sending a message — each is shown and confirmed unless your `answers.yaml` policy says otherwise.
- **NA specifics.** Letter paper, one page, no photo or personal-data block; hard constraints are work authorization / sponsorship / location / years / band; pipeline is APPLIED → SCREEN → OA → TECH → ONSITE → OFFER; outreach is LinkedIn notes and cold email, not chat openers.
- **No agent framework.** Skills are Markdown; the MCP server is ~300 lines of Python on `httpx`.

## What changed from ASu-skills

Chinese 秋招 pipeline → NA pipeline · Boss直聘 / WeChat openers → LinkedIn / email · 学历 / 年龄 constraints → work authorization / years / band · A4 + photo templates → one Letter template · JSON claim ledger → `facts.md` · Kimi WebBridge → the host browser · 18 templates and multi-platform manifests dropped · `/career-init` and jobs-mcp added.

## License

MIT. Portions adapted from ASu-skills © Hisn0w, MIT.
