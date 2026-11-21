# Mature AI job agents: what they do and what job-agent can learn (2026-11-20)

Sources are mostly reviews and vendor pages; prices are approximate (several vendors hide them).

| Product | Core loop | Auto-apply | Human approval | Biggest complaint |
|---|---|---|---|---|
| Jobright.ai | match-scored feed → tailored resume → autofill → insider connections → chat copilot | "Agent" (beta) | autofill yes, agent partly | paywalls, failed submits, autofill typing wrong info |
| Simplify | free Chrome autofill for 100+ portals → auto-tracker → matches | Autopilot, 20/week (paid) | Copilot yes, Autopilot no | missed fields, feeds volume applying |
| Teal | job clipper → tracker → keyword match → AI bullets | no | yes | AI paywalled, no automation |
| Huntr | kanban CRM, clipper, autofill, tailored resume, mobile | no | yes | free cap, AI is an add-on |
| LazyApply | one-click mass apply on LinkedIn / Indeed | yes (bot) | no | LinkedIn bans, refunds, misfires |
| AIApply | resume + cover letter, auto-apply, interview buddy | yes | optional | wrong targeting, "Frankenstein" resumes |
| JobCopilot | cloud agent, 20–50 applications/day | yes (server) | opt-in | scam/ghost jobs, breaks on Workday |
| LoopCV | daily auto-apply loops + recruiter emails | yes | semi-auto | matched ≠ applied |
| Jobscan | resume vs JD keyword score | no | yes | score doesn't predict callbacks |
| Indeed Career Scout, LinkedIn AI | conversational search, autofill (Indeed), network-based tracker (LinkedIn) | inside their apps | yes | walled gardens |

## What they converge on
Free Chrome autofill as the wedge; a match-scored job feed as the home screen; tracking with no manual step; a reusable answer bank; referrals and connections; tiers from manual to capped auto-submit to cloud bots (the best-reviewed sit at the assisted end); trust signals on postings.

## Where job-agent is different
- **No fabrication:** the top complaint across products is invented skills and metrics the candidate can't defend; job-agent blocks any number not in `facts.md` with a deterministic gate.
- **Targeting:** APPLY/SKIP with hard constraints and the posting guard vs wrong-level, wrong-location and scam applications.
- **Account safety:** stops before Submit, reads public ATS endpoints; no bans.
- **Interview prep tied to the resume** (prep-graph), not generic Q&A.
- **Evals and calibration:** no competitor publishes outcome data or a baseline.
- **Data ownership:** local markdown (Sonara shut down in 2024 and users lost their data).

## Where they are ahead
Distribution (one-click extension vs a coding-agent install), ATS coverage (Workday, iCIMS, Taleo), speed, a push feed with alerts, referrals, polish and mobile.

## Ideas, in priority order
1. Referral / connection finder per APPLY verdict, with a facts-traced note.
2. Match-score feed in the tracker app with one-click APPLY / SKIP.
3. Workday / iCIMS / Taleo autofill recipes plus a growing answers.yaml bank.
4. Auto-log the tracker row on Submit.
5. Provenance view: each resume line shows its facts.md source.
6. Posting trust score (repost age, no salary, off-domain apply link).
7. Capped batch mode: prepare 5, approve on one review screen.
8. Publish calibration numbers (interview rate by source vs baseline).

Sources: jobright.ai, simplify.jobs/copilot, tealhq.com, huntr.co, Trustpilot pages for LazyApply / AIApply / JobCopilot / Massive, scoutify.com reviews, blog.loopcv.pro (Sonara), indeed.com/careerscout, news.linkedin.com (2026), axios.com (2026-08-21).
