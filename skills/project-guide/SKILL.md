---
name: project-guide
description: Turn a repository or project description into study material or interview material — a source-code course (tutorial.md + practice.md, lesson by lesson along real call chains) or a study guide + interview prep pair (guide-<slug>.md, interview-<slug>.md with pillar-first resume bullets, 15–25 questions, first-person STAR answers, and a source-evidence index). Use when the user types /project-guide, wants to learn a codebase, build a project deep-dive, generate a question bank, or prepare a project for tech deep-dive interviews.
---

# /project-guide — Learn it, explain it, survive the follow-ups

Two modes. **Course**: learn any repo lesson by lesson along real call chains. **Guide + interview**: turn one of your own projects into interview-grade material. Never invents companies, titles, numbers, launch results, or personal responsibilities.

## Routing

Course / practice / learning path / interview prep from a repo → **here**. Bullets only → `/great-resume`. Mock interview on an existing resume → `/interview`. HTML/PDF → `/make-resume`. PRs → `/contributor`.

## Input contract

Read the workspace first. Mode from the request; default guide + interview. Ask ≤ 3 high-signal questions; `[TBD]` when the user wants a draft first.

| Field | Required | Notes |
|---|---|---|
| Source code | course | local repo; a description alone cannot yield a verified call path |
| Project description | guide + interview | context, goal, responsibility, hard parts, results |
| Operation | course | outline, expand lesson N, practice for lesson N, or an explicit combination |
| Slug | recommended | `guide-<slug>.md`, `interview-<slug>.md` |
| Stack / target role | no | |

Thin material → ask: personal responsibility and collaboration boundary? the hard part and how before/after was verified? evidence (metrics, logs, PRs, release records)?

## Course mode

Files `tutorial.md` and `practice.md`. Location: the repo root for the user's own repos; `career/learning/<repo>/` for third-party repos. Without a specific operation, produce the outline only.

- **Outline** — [references/course-outline-design.md](references/course-outline-design.md): entry points, main features, module boundaries, one representative end-to-end run; each lesson lists real files/symbols in reading order; record source version, coverage, uncovered modules.
- **Expand a lesson** — [references/course-lesson-design.md](references/course-lesson-design.md): follow the real call/event order; update only that lesson.
- **Practice** — [references/course-practice-design.md](references/course-practice-design.md): questions only, matched to lesson numbers; only what the lesson taught.

Source facts: every file/function/event locatable; implementation beats docs; async and DI traced to registration/consumption or marked `UNCONFIRMED`; only implemented error/recovery paths; no unmeasured performance claims; partial updates keep the user's notes.

## Resume bullet constraints

Before `interview-<slug>.md`, read [references/examples/bullet-few-shots.md](references/examples/bullet-few-shots.md) — structure only, never its content. Extract 4–6 **architectural pillars**; each top-level bullet starts with `**<Generic pillar>:**` then problem/evolution → mechanism → constraints → result (real metric or a measurement plan). Implementation names go to the evidence index. Bullets are candidates until they pass `career/rules.md` and trace to `career/facts.md`.

## Deliverables

| Mode | File | Content |
|---|---|---|
| course | `tutorial.md` | outline + expanded lessons |
| course | `practice.md` | questions by lesson |
| guide + interview | `guide-<slug>.md` | learning path, reading order, principles, decisions, verification |
| guide + interview | `interview-<slug>.md` | resume summary, pillar bullets, questions, STAR answers, evidence index |

Own projects default to `career/projects/<slug>/` (private). Cannot write → labelled Markdown blocks.

### `guide-<slug>.md`
1. Prerequisites (frequency-tagged) · 2. Highlights and learning order (3–6, generic engineering titles, files first, order) · 3. Must-know checklist · 4. Recommended reading with relative paths and "what you can answer after" · 5. Self-study reminder (fixed: ask the AI when a file is unclear; this skill gives path and questions, not line-by-line teaching) · 6. Technical positioning · 7. Core principles (problem → mechanism → where it lands) · 8. Key design decisions (alternatives / trade-off / risk / verification) · 9. Quantification and verification (`to measure` where no data).

### `interview-<slug>.md`
1. Project summary (1–2 sentences, no internal names) · 2. Resume bullets (4–6) · 3. 15–25 main questions in 3–6 themes, each main with ≥ 2 follow-ups, **every answer first-person, ≥ 120 words, STAR order symptom → cause → action → result/fallback** · 4. Source-evidence index (paths, symbols, private fields, telemetry names live here).

Internal-name budget: ≤ 2 per main answer (each followed by the generic explanation), ≤ 1 per follow-up. Over → rewrite.

## Hand-offs (append to the reply)

**For `/great-resume`** — project, role, boundary, key actions, evidence, candidate wording, `TODO:` facts.
**For `/interview`** — Ownership / Metric / Architecture / Result claims to drill.

## Quality gate

Mode and files right · course symbols locatable, order real · lesson/practice consistent, user notes untouched · inference and unmeasured benefit labelled · both files present · pillar-first bullets, one pillar each, problem + mechanism + result · 15–25 questions, ≥ 120-word answers · evidence index present · no team results as personal, no invented metrics or titles.
