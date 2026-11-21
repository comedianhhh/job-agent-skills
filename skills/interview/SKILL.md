---
name: interview
description: Resume- and JD-driven interview prediction, mock interview with contract-based follow-up questioning, evidence review, and weak-spot retry, structured around North American rounds (recruiter screen, OA, technical, system design, behavioral). Use when the user types /interview, asks to predict questions, run a mock or stress interview, drill a resume claim, practise system design or STAR answers, or check how well they can defend what the resume says.
---

# /interview — Interrogate the resume

`/interview` does not write answers to recite. It turns the important claims on the resume and in the JD into verifiable questions, and checks — through an interview contract, one question at a time, evidence scoring, and targeted retry — whether the user can explain real responsibilities, implementation, metric definitions, trade-offs, and failures.

```text
resume / JD → claims + role-competency matrix → interview contract → question & scoring contract
           → one question at a time, dynamic follow-ups → session ledger → evidence review + retry
```

## Inputs

1. The role's resume (`<folder>/01-Resume.html`) and `career/facts.md` — including its `TODO:` lines, which are exactly the numbers an interviewer will probe.
2. The JD (`<folder>/03-Job-Description.md`).
3. `career/stories.md` (`[fact]` vs `[draft — confirm]`).
4. Round, time available, feedback preference.
5. What the company is betting on right now, not just the JD: its product page, recent blog posts or news, and the interviewer's own public posts. The JD lists a stack; this says which problem they most want solved.

**Before saying something is missing** (a gap, "no evidence", "not listed", "not yours"), check every source, not the first one that loads: `career/facts.md`, `stories.md`, `blocks.md`, the user's repos (local clones beside `career/`, and `gh repo list <user>` from the GitHub link in `facts.md` when `gh` is available), and for pay or hours every page of the company's careers site, other language versions included. A hit outside `facts.md` is `UNCONFIRMED`: name the file and ask the user to confirm it (then add it to `facts.md`), never a gap. Every gap names the sources it was checked against.

No JD → predict from the resume. No resume → ask for one project. Ask only for what materially changes the drill; otherwise use defaults. Unknowns are `UNCONFIRMED`; never fabricate experience, numbers, or technical detail. Save a review to disk only on request (default: the role's `04-Interview-Prep.md`); never into a public file.

## North American rounds

| Round | Tests | Default focus |
|---|---|---|
| Recruiter screen | 60-second pitch, authorization, comp, motivation | intro script, logistics |
| OA / coding | DS&A, take-home | out of scope unless asked |
| Hiring-manager / phone technical | one project end-to-end | Ownership + Technical + Architecture claims |
| Onsite — coding | live coding | out of scope unless asked |
| Onsite — system design | one subsystem in depth for mid-level; breadth + trade-offs for senior | `references/scenario-interviews.md` |
| Onsite — behavioral | STAR, conflict, failure, leadership | `stories.md` index |
| Onsite — HM / bar raiser | consistency with everything already said | ledger contradictions |

## Modes

### Predict — `/interview predict`
Research the company first (input 5), then choose the lead project: the one closest to the problem their current product solves, not the one closest to the JD stack. Example: a TMS whose AI turns emails into orders → lead with a document-classification / human-review project, not a real-time networking one, even though the JD says WebSockets. When new research changes the pick, re-check every section that names a project, not only the one in front of you. Then extract Ownership / Metric / Technical / Architecture / Result claims; build `competency — evidence — gap` from the JD (gap cells only after the all-sources check above, each listing what was checked); rank by relevance × probability × wording risk × evidence gap; output high-probability, supplementary, and stress questions. Per core question: source, intent, facts the answer must cover, next follow-up. No long model answers.

```text
Q: Why did you choose an event-sourced store instead of updating rows in place?
Source: resume — "designed the ingestion pipeline … replayable"
Intent: technical choice, decision authority, trade-off
Answer must cover: original problem, alternatives, why this one, your part, result evidence
Follow-up: what breaks first at 10× the event volume?
```

### Grill — `/interview grill`
Build the contract ([references/interview-contract-and-session.md](references/interview-contract-and-session.md)); lock a scoring contract before each question ([references/question-and-scoring-contract.md](references/question-and-scoring-contract.md)); **one question per turn**; dig / clarify / step down / switch / end based on evidence; feedback per policy (immediate = training, deferred = realistic); keep the ledger. Scenario or system design → [references/scenario-interviews.md](references/scenario-interviews.md). Never give the answer before the user answers; hints only as agreed, never project facts.

### Review — `/interview review`
From the ledger: verified / partial / unverified / contradictory claims with the answer evidence; what needs a fact, knowledge, or toned-down wording; the two follow-ups most likely to expose the user; prioritised actions. No total score. Template: [references/review-and-retry.md](references/review-and-retry.md).

### Retry — `/interview retry`
Only `partial` / `unverified` / `contradictory` claims; variants and counterfactuals, not repeats; compare evidence with last time; passed claims leave the queue.

### Cheat sheet — `/interview cheatsheet`
A one-page glance sheet for the last hour before the call, written to `<folder>/05-Cheat-Sheet.md`. It is for scanning, not reading:

- **Keywords, never sentences.** English terms the user should say (project names, numbers with their unit and period, stack, the interviewer's product names), each with a short hint in the user's working language: the language they talk to you in. No full English sentences, no scripted answers; a script turns into reading aloud.
- **Date and time from `career/tracker.md`** (that row's next step), never from memory or the JD. If the tracker has none, write `TBD — not in tracker` and ask the user.
- Tables, in this order: interview (company, role, round, date/time, interviewer) → pitch beats (3–5 keywords) → the claims they will probe, each with number / baseline / period → company-specific hooks (from input 5) → questions to ask them → don'ts (team numbers, `TODO:` facts, anything `UNCONFIRMED`).
- Facts only from `career/facts.md`; a `TODO:` number never appears, not even as a keyword.

```markdown
| Keyword | 提示 |
|---|---|
| webhook + event log | 替掉 cron 轮询；15 min → <30 s（2025-03） |
| idempotency key + reconciliation | 重复事故 3–4/月 → 0（6 个月） |
```

## Claims and what to probe

- **Ownership** — personal scope, what you built by hand, decisions, team split. Project result ≠ personal result.
- **Metric** — baseline, denominator, period, data source, attribution.
- **Technical** — inputs/outputs in *this* project, why this technique, the trade-off. Definitions do not count.
- **Architecture** — components, data flow, boundaries, alternatives, failure handling, scaling limits.
- **Result** — shipped or not, who uses it, how measured, personal vs. team.

Chase first: vague verbs without object/evidence; numbers without a measurement definition; "led / architected" without a boundary; happy path only; term definitions without project role; contradictions with the resume or earlier answers.

```text
sufficient → ≤ 1 alternative / counterfactual → close claim
partial    → probe only the critical missing piece
no idea    → step down to the smallest fact → still nothing → unverified, switch
two answers with no new evidence → stop the branch
budget reached → wrap up → Review
```

When the resume is stronger than the user can defend, offer exactly three paths: add a real fact, learn the missing knowledge, or tone the wording down. Changes to `facts.md` / `stories.md` only with confirmation.

## Spoken register

Anything the user will say out loud — a pitch, a background walkthrough, a STAR answer, a model phrasing offered as a hint — is written for the ear, not the page. Polished parallel prose reads as machine-written the moment it is spoken.

- Short sentences, contractions, one idea per breath. Spoken connectors are expected: "so", "basically", "the thing I did was", "and then".
- Open like a person answering ("Sure. So, quick version —"), not with a thesis statement.
- When the user asks for a pitch or script, hand over one finished version built from the research (the interviewer's own posts, shared history, the company's product names) — not a draft to polish over several rounds. Drill after.
- Lead with strengths. Don't volunteer limitations or "how I learned it"; answer a direct question truthfully.
- Order by relevance, not by time. A pitch or "tell me about yourself" leads with the one story closest to this role (the problem + one number), compresses the rest of the background into one sentence, and ends on why them. Never walk the career job by job — that reads as a resume read aloud.
- No taglines, no parallel slogans, no closing summary line. End on a fact or a one-line "that's what got my attention", then stop.
- Plain verbs over résumé verbs: swapped / fixed / built / made sure, not replaced / eliminated / architected / ensured.
- Approximations and one small self-correction are allowed ("about 75%", "like, ten hours a week") — that is how real recall sounds.
- Facts and numbers are unchanged and still come only from `career/facts.md`.
- Test before handing it over: read it aloud. If it sounds like a LinkedIn About section, rewrite.
- Pair every script with a beat skeleton (per beat: where / what you did / number / why it matters to them) and have the user say it back in their own words. The skeleton is the deliverable; the script only shows how the beats connect.

## Sequence

`/job-match → /great-resume → /make-resume → /job-apply → /interview → /offer`. The resume is written for the recruiter; the follow-ups are reserved for the facts.
