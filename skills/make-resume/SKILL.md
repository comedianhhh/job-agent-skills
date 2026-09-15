---
name: make-resume
description: Create or tailor the one-page Letter resume and cover letter for one application folder under career/, then export both to PDF with scripts/export-pdf.sh and enforce the one-page gate. Use when the user types /make-resume, asks to build, tailor, regenerate, or export a resume or cover letter for a role, or to open a new application folder.
---

# /make-resume — Produce the files for one application

The only entry point that creates or edits resume and cover-letter files. One template (`career/application/` + `career/resume.css`, Letter, single page), so every version stays consistent. No photo, no personal-data block, no alternative templates.

## Routing

- Wording only → `/great-resume`. Fit / which master → `/job-match`. Files → **here**.

## Inputs

1. The folder `career/YYYY-MM-DD-Company-Role-ReqID/`. If missing: copy `career/application/` to that name and fill `03-Job-Description.md` first (or run `/job-match`) — **JD analysis before any resume edit**.
2. Which existing folder is the master for this track (backend / full stack / AI …). A new role changes the headline, the company-description line, and 1–2 bullets — about 20 minutes, not a rewrite.
3. `career/facts.md`, `career/blocks.md`, `career/rules.md`. Only confirmed facts; `TODO:` never.

Ask only for what blocks delivery. Unknown field → visible `[TBD]` in the draft; never export a PDF containing one.

## Workflow

1. **Resume** — edit `<folder>/01-Resume.html`; keep `<link rel="stylesheet" href="../resume.css">`. Per-role style tweaks go in an inline `<style>`, never in the shared CSS. Sections: Experience, Projects, Skills, Education. Dates `MMM YYYY – Present`; locations `City, Region` or `Remote`. Order sections by the JD's priorities; front-load the strongest anchor.
2. **Cover letter** — `<folder>/02-Cover-Letter.md`: hook → three JD priorities each backed by a hard fact → one honest gap paragraph, pivot to depth → close with why this company and work authorization in one clause. Body after the `---` rule is what the exporter renders. ≤ 1 page.
3. **Export** — from the project root:

   ```bash
   sh scripts/export-pdf.sh "career/<folder>" "<Company-Role>" "<Full Name>"
   ```

   (When installed as a plugin, the script is at `${CLAUDE_PLUGIN_ROOT}/scripts/export-pdf.sh`.) It writes `<Company-Role>-<Name>.pdf` and `<Company-Role>-Cover-Letter-<Name>.pdf` and prints page counts.
4. **Gate** — both PDFs must be `1 page(s)`. Two pages is a defect: cut or tighten; never shrink fonts below the stylesheet. Links visible as text; no `[TBD]` / `TODO`.
5. **Freeze** — after submission, commit the folder (`apply(<Company>): <Role>`) so the sent version is recoverable; add the row to `career/tracker.md` (`/offer`).

## Deliverable

Folder path, the master used, what changed vs. the master, both PDF paths with page counts, open `[TBD]`s. Never copy contact details or the private folder into anything public.
