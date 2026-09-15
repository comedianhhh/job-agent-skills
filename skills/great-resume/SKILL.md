---
name: great-resume
description: Reposition real experience for a target role using only career/facts.md — positioning line, summary, bullet rewrites into career/blocks.md, a LinkedIn recruiter note, cold email, and a short self-introduction. Use when the user types /great-resume, asks to strengthen or rewrite experience or project bullets, or wants recruiter outreach text. Building the HTML/PDF file is /make-resume.
---

# /great-resume — Make real experience read stronger

Translate what the user did into language a North American recruiter scans in 20 seconds, a hiring manager can follow up on, and a reference check can verify. Positioning and evidence organisation — never invented titles, companies, stacks, or numbers.

## Files

| File | Role |
|---|---|
| `career/facts.md` | Truth. Nothing goes out that is not here. `TODO:` items never go out. |
| `career/blocks.md` | Finished bullets. Prefer an existing block; add a new one here rather than rewriting from scratch each time. |
| `career/rules.md` | The review standard. |
| `career/stories.md` | The "can I defend this?" check for every strong claim. |

Claim status lives in `facts.md`: confirmed (dated ✅ or plain fact), unconfirmed (`TODO:`), stale (changes over time — re-verify), do-not-use (user decided).

## Workflow

1. Confirm the target role, the JD (usually `<folder>/03-Job-Description.md` after `/job-match`), the channel, and what to emphasise.
2. Read the facts and the existing resume. Conflicting sources → do **not** pick the flattering one; mark unconfirmed and list it. Missing material → draft from what exists, list ≤ 5 must-fill items.
3. Offer 1–3 positioning lines: a safe and an ambitious version; the ambitious one states the evidence it still needs.
4. Rewrite bullets as **action → system capability → business value → result evidence → personal boundary**. Reuse `blocks.md`; new blocks get added there (with the user's OK) so they are never lost.
5. Produce the summary, a recruiter note, and a slightly longer self-introduction.
6. Audit strong claims: original → proposed → fact → boundary → risk. Update `facts.md` only with confirmation.

## Boundaries

- Titles, companies, dates, education: exactly as recorded.
- "Led / owner / architected / founding" only with decisions, delivery, and result the user can explain.
- No number without a source; qualitative beats invented.
- Team work is written as team work. Borrowed names (investors, partners, awards) go in the company line; the user's work goes in bullets. Unverifiable names are deleted, not hinted.
- Unreleased work: what was built, never the outcome. Shipped work must say shipped.
- Never volunteer a weakness in outgoing material.
- Files → `/make-resume`. Status → `/offer`.

## Deliverable order

1. one-line positioning; 2. summary; 3. 2–4 bullets, each tagged with its `blocks.md` block or `new block`; 4. recruiter note + self-intro; 5. evidence to strengthen + likely follow-ups.

## Outreach formats

- **LinkedIn connection note** — 300-character limit. Who you are + one verifiable result + a specific ask. No "passionate".
- **InMail / follow-up** — 3–5 sentences: role + req ID, one anchor, one number, one question. Sent 10 business days after applying with no reply.
- **Cold email to a hiring manager** — subject names the role; ≤ 120 words; one link; no attachments unless asked.
- **Referral request** — which role, why this person, and a two-line blurb they can paste.

All in English; no salary or visa unless asked. Work authorization, if asked, in one clause from `answers.yaml`.
