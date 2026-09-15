---
name: evidence-recap
description: Reconstruct an AI-assisted coding session or a project's delivery records into a verifiable nine-part evidence chain — problem, decision, personal actions, delivery stage, scope, effect evidence, personal boundary, missing evidence, interview follow-ups — and feed confirmed facts into career/facts.md. Use when the user types /evidence-recap, finishes a build session and wants it captured, or asks what a piece of work actually proves. Not for resume rewriting (/great-resume), source study (/project-guide), or mock interviews (/interview).
---

# /evidence-recap — Turn a session into evidence

AI-assisted builds produce a lot of activity and little *provable* evidence unless captured while the context is fresh. Reconstruct a conversation or delivery record into a chain that shows the problem, the decisions, what the **user** did (vs. the model, the team, a platform), how far it shipped, and what it proves — so the user can decide whether it deserves a resume line, a story, or more work.

## Scope

Only: AI coding conversations (transcripts, commit history produced during them); design / implementation / integration / acceptance / delivery records; material showing whether something shipped, its effect, and who owned what. No resume edits here.

## Workflow

1. Treat the user's decisions, verifiable results, and key assistant reasoning as material. Speculation is not fact.
2. Privacy pass: generalise project code names, tokens, keys, emails, customer identifiers, internal paths, unpublished architecture. Unannounced products get a generic descriptor.
3. Determine the **delivery stage** first: `production` / `internal pilot` / `prototype - technical validation` / `planned - estimated`. Only what the material supports.
4. Output the nine parts in order. Do not paper over gaps.
5. If the user submits their own rewrite later, respond only with: facts preserved, density moves that hold, statements that overreach.

## The nine parts

1. **Problem context** — scenario, prior problem, constraints, intended outcome.
2. **Decision** — approach, why, what was rejected, trade-offs.
3. **Personal actions** — what the user actually did (design, implementation, integration, verification, driving). AI-written code, team work, and platform features are labelled separately: "AI wrote the code; the user specified, reviewed, tested, decided" is a legitimate, specific statement.
4. **Delivery stage** — explicit.
5. **Scope** — environment, users/teams, duration, surface covered.
6. **Effect evidence** — each item `measured` / `interim` / `technical validation` / `estimated`, with the metric's original scope (a team-internal number stays team-internal).
7. **Personal boundary** — owned / participated / integrated / verified / did not own. Team or platform results are never promoted.
8. **Missing evidence** — users, scope, dates, metrics, acceptance, usage records that are absent. Not inferred. These become `TODO:` lines if the item enters `facts.md`.
9. **Interview follow-ups** — trade-offs, failure paths, scope, effect, ownership questions the material *can* answer. Hand to `/interview`.

## Boundaries

Shipped / piloted / prototyped / planned always distinguished. Measured / interim / validated / estimated always distinguished. No number without a source. No secrets or internal names. A demo is never a launch; an estimate is never an achieved result. Every named mechanism maps to real behaviour in the material.

## Appendix: density upgrade

After the nine parts add a **density upgrade** by default; add **candidate resume wording** only when asked (then route to `/great-resume`). At most: one raw-fact sentence; one high-density sentence linking fact → mechanism → impact; the moves used; one optional rewrite prompt.

Moves: **high density** (fact + mechanism + impact in one sentence) · **high leverage** (key decision, causal lever, personal action; adjectives do no work) · **high dimension** (mechanism, stage, evidence type, boundary, and value at once).

## Where it goes

Default: the conversation. On request: `<application folder>/05-Evidence-<slug>.md`, or a `[draft — confirm]` entry in `career/stories.md`. Facts that pass confirmation go into `career/facts.md` with a date.

## Pre-send check

nine parts in order · stage and effect tagged · personal vs. team/platform/AI separated · gaps in part 8, not inferred · privacy pass done · density upgrade present · resume wording only if asked.
