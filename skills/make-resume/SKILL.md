---
name: make-resume
description: Create or tailor the one-page Letter resume and cover letter for one application folder under career/, then export both to PDF (career/render-resume.sh when the workspace has one, else scripts/export-pdf.sh) and enforce the one-page gate. Use when the user types /make-resume, asks to build, tailor, regenerate, or export a resume or cover letter for a role, or to open a new application folder.
---

# /make-resume — Produce the files for one application

The only entry point that creates or edits resume and cover-letter files. One template per workspace — whatever `career/application/01-Resume.html` is — Letter, single page, so every version stays consistent. No photo, no personal-data block, no alternative templates.

**Workspace layout rule (hard).** Read `career/rules.md` → Format first. If the workspace has `career/render-resume.sh` (a dual-column workspace: `career/resume-base.css` + `career/dep/`), then:
- every `01-Resume.html` is a copy of `career/application/01-Resume.html`, the dual-column template (`#main` with date column + `#sidebar` with Contact / Portfolio / Summary / Technical Skills), linking `../dep/normalize.css/normalize.css`, `../dep/Font-Awesome/css/font-awesome.css` and `../resume-base.css`;
- the single-column `resume.css` is never used, even if the file still exists;
- export **only** with `sh career/render-resume.sh` — never call `scripts/export-pdf.sh` directly for the resume (it rewrites only `../resume.css`, so a dual-column page prints without its stylesheets).

Without `render-resume.sh`, the default single-column template (`career/application/` + `career/resume.css`) and `scripts/export-pdf.sh` apply.

## Routing

- Wording only → `/great-resume`. Fit / which master → `/job-match`. Files → **here**.

## Inputs

1. The folder `career/YYYY-MM-DD-Company-Role-ReqID/`. If missing: copy `career/application/` to that name and fill `03-Job-Description.md` first (or run `/job-match`) — **JD analysis before any resume edit**.
2. Which existing folder is the master for this track (backend / full stack / AI …). A new role changes the headline, the company-description line, and 1–2 bullets — about 20 minutes, not a rewrite.
3. `career/facts.md`, `career/blocks.md`, `career/rules.md`. Only confirmed facts; `TODO:` never.

Ask only for what blocks delivery. Unknown field → visible `[TBD]` in the draft; never export a PDF containing one.

## Workflow

1. **Resume** — edit `<folder>/01-Resume.html`, copied from `career/application/01-Resume.html`; keep its stylesheet links exactly as the template has them. Per-role style tweaks go in an inline `<style>`, never in the shared CSS. Order content by the JD's priorities; front-load the strongest anchor. Locations `City, Region` or `Remote`.
   - **Dual-column workspace:** main column = Professional Experience, Projects, Education (`.blocks` with the date column: end date on top, start date below, `MM/YYYY`); sidebar = Contact Info, Portfolio, Summary, Technical Skills (`dl.skill-groups`, ordered by the JD).
   - **Single-column workspace:** sections Experience, Projects, Skills, Education; dates `MMM YYYY – Present`.
2. **Cover letter** — `<folder>/02-Cover-Letter.md`: hook → three JD priorities each backed by a hard fact → one honest gap paragraph, pivot to depth → close with why this company and work authorization in one clause. Body after the `---` rule is what the exporter renders. ≤ 1 page.
3. **Review (second agent)** — the drafter does not grade its own draft. In Claude Code, dispatch the `application-reviewer` subagent (shipped in this plugin's `agents/`) with the folder path, `career/facts.md`, `career/rules.md`, and the posting-integrity verdict from `/job-match`. It starts with a fresh context, researches the company from its official site, reads the drafts as the hiring manager would, and returns at most eight `old` / `new` edits, each tied to a requirement and a `facts.md` section, plus gaps to leave honest. It cannot write files.
   - Apply an edit only after checking its source line in `facts.md` yourself; reject any edit that adds a fact, overstates ownership or stage, or covers a gap. Say which edits were applied and which rejected, and why.
   - A company fact the reviewer found may go into the letter only with its URL kept in your notes; employer numbers ("40M users") still have to pass the trace gate, so confirm them with the user and pass the source with `--also`, or leave them out.
   - Hosts without subagents (pi): do the same pass yourself after re-reading the posting, `facts.md`, and both drafts from disk, with the same output format; say that the review was not independent.
4. **Export** — dual-column workspace, from `career/`:

   ```bash
   sh render-resume.sh "<folder>" "<Company-Role>"
   ```

   It refuses any `01-Resume.html` that does not link `../resume-base.css`, runs `export-pdf.sh` for the trace gate and the cover letter, re-renders the resume from the folder, and fails unless the resume is one page. Single-column workspace, from the project root:

   ```bash
   sh scripts/export-pdf.sh "career/<folder>" "<Company-Role>" "<Full Name>"
   ```

   (When installed as a plugin or package, the script is at `<install root>/scripts/export-pdf.sh` — `${CLAUDE_PLUGIN_ROOT}` in Claude Code, the package directory that contains this skill's `skills/` folder in pi.) It writes `<Company-Role>-<Name>.pdf` and `<Company-Role>-Cover-Letter-<Name>.pdf` and prints page counts.
5. **Gate** — three checks, all deterministic:
   - **Trace** — `export-pdf.sh` (also inside `render-resume.sh`) runs `scripts/check-trace.py` first and refuses to export when a number in the resume or letter body (75%, 3x, 256, 4.5) is not in `facts.md`, or a `TODO` / `[TBD]` is left. An `UNTRACED` line means one of two things: the number is wrong (fix the line) or the fact is real but missing from `facts.md` (ask the user, add it there with its source, re-run). Never reword a number to dodge the check, and never set `SKIP_TRACE=1` on your own.
   - **Pages** — both PDFs must be `1 page(s)`. Two pages is a defect: cut or tighten; never shrink fonts below the stylesheet. Links visible as text. **Cut by relevance, not by age:** run

     ```bash
     python scripts/rank-cuts.py "career/<folder>"
     ```

     It scores every bullet on relevance to the posting (BM25, 0.60), uniqueness against the other bullets (0.25) and how much the cover letter reuses it (0.15), lowest first. Cut or shorten from the top of that table, one line at a time, re-exporting after each — unless the line is the only evidence for a high-weight `MATCHED` requirement in `03-Job-Description.md`, which the table cannot see. Never trim the oldest role by default.
   - **ATS** — after the final export, read the PDF the way a parser does:

     ```bash
     python scripts/check-ats.py "career/<folder>"
     ```

     `FAIL` blocks delivery: no text layer, an email or phone that is not literal text (icon glyphs, image), or bullets that come out spliced with other text (a sidebar read into the middle of a bullet). Fix the template or markup and re-export; never paste hidden text to satisfy it. `WARN` lines (name not at the top of the text layer, links only as hyperlinks, icon-font glyphs) go in the deliverable. Keyword lines are information: a term "in facts.md, not the resume" may be added if the job needs it — through `blocks.md`, then trace gate again; a term "in neither" is a gap and is never added. Exit 3 means no extractor is installed (`pip install pypdf`); say the check was skipped.
6. **Freeze** — after submission, commit the folder (`apply(<Company>): <Role>`) so the sent version is recoverable; add the row to `career/tracker.md` (`/offer`).

## Deliverable

Folder path, the master used, what changed vs. the master, reviewer edits applied / rejected, any lines cut (with their rank-cuts score), both PDF paths with page counts, the `check-ats` summary line and its warnings, open `[TBD]`s. Never copy contact details or the private folder into anything public.
