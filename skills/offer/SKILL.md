---
name: offer
description: Maintain the application pipeline in career/tracker.md — new applications, recruiter screens, OAs, interview loops, offers, rejections, follow-ups — from emails, screenshots, or chat, and run the daily new-postings scan through jobs-mcp using career/targets.yaml. Use when the user types /offer, reports an interview invite, rejection, or offer, asks what to follow up on, wants the pipeline summarised, or asks to scan for new jobs.
---

# /offer — Pipeline tracking and scanning

One record: `career/tracker.md`. No side spreadsheets.

## Statuses

| Status | Evidence |
|---|---|
| `DRAFT` | folder exists, nothing sent |
| `BLOCKED` | materials ready, hard constraint unresolved — do not apply |
| `APPLIED` | confirmation page or "application received" |
| `SCREEN` | recruiter / hiring-manager call scheduled or done |
| `OA` | assessment or take-home link |
| `TECH` | phone technical or virtual rounds in progress |
| `ONSITE` | final loop scheduled |
| `OFFER` | written offer (record base / bonus / equity / deadline in Next step) |
| `REJECTED` | explicit rejection — note the stage |
| `GHOSTED` | no reply ≥ 3 weeks after the last touchpoint, after one follow-up |
| `WITHDRAWN` | user withdrew |

Only change a status on evidence. An automatic receipt is `APPLIED`, never `SCREEN`. Unclear → keep the status, write `unconfirmed` in Next step.

## Updating

1. Extract date, company, role, req, new status, next action, deadlines (OA expiry, offer deadline, interview time with timezone).
2. Merge into the existing row; later stages overwrite earlier. New row only for a new application (respect `max_roles_per_company`).
3. Next step is an action with a date: `follow up on LinkedIn 2026-09-26`, `OA due 2026-09-20 23:59 ET`, `loop 2026-09-22 — run /interview grill system_design`.
4. Follow-up: 10 business days after `APPLIED` with silence → one LinkedIn message (`/great-resume` outreach format), note the date; ~2 more weeks → `GHOSTED`.
5. Interview scheduled → suggest `/interview` on that folder and a fresh 1-page export if the sent version was 2 pages.
6. Offer → record the numbers; never negotiate or send anything.

## Scanning (needs jobs-mcp)

Read `career/targets.yaml`; call `scan` with `boards_`, `linkedin_queries`, `hours`, `include_regex`, `exclude_regex`, `location_regex`. Append results to `career/SCAN-<YYYY-MM-DD>.md` as `| Company | Role | Location | Posted | URL | first-look GAP |`, then for each promising posting either run `/job-match → /make-resume → /job-apply` the same day or list it for the user (portals they handle themselves). Drop postings that violate `max_years_required` or `salary_floor` when the posting states them. Never re-list a URL already in the tracker or a previous scan.

If `jobs-mcp` is not available, say so and give the manual URLs (`boards.greenhouse.io/<token>`, `jobs.lever.co/<company>`, `jobs.ashbyhq.com/<org>`).

## Mailbox triage

Use the browser; the user logs in (never handle passwords, MFA, codes). Search by company, "interview", "assessment", "application". Map: received/thank you → `APPLIED`; recruiter call → `SCREEN`; HackerRank/CodeSignal/take-home → `OA`; technical interview → `TECH`; onsite/final → `ONSITE`; offer → `OFFER`; "not moving forward" → `REJECTED`. Copy no email bodies — company, role, status, date, next step only.

## Deliverable

Rows changed (before → after, one-phrase evidence) · deadlines and interviews in the next 7 days · follow-ups due now · missing information to supply. `career/tracker.md` stays private.
