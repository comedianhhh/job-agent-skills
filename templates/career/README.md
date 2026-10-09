# career/ — your private job-search workspace

Created by `/career-init`. Every skill in job-agent-skills reads and writes **only** these files.
Keep this folder in a **private** repo: it holds your phone number, where you are applying, and honest notes about your gaps.

| File | What it is | Who writes it |
|---|---|---|
| `facts.md` | The single source of truth: everything you actually did, with numbers and `TODO:` markers for what you still need to confirm. Every resume line must trace back here. | you (+ `/evidence-recap`, `/contributor` with your confirmation) |
| `blocks.md` | Finished, copy-ready resume bullets in English. New resumes are assembled from these, not rewritten from scratch. | `/great-resume` |
| `stories.md` | Interview stories (STAR) indexed by question type, marked `[fact]` or `[draft — confirm]`. | you, `/evidence-recap`, `/interview` |
| `rules.md` | Your resume-review standard — what a bullet must answer, what gets cut. | you |
| `answers.yaml` | Standing form answers: contact, work authorization, pronouns, years of experience, EEO choices, salary floor. `/job-apply` fills forms from this. | you |
| `targets.yaml` | Boards to scan and your hard filters. `/offer` scans with these via jobs-mcp. | you |
| `tracker.md` | The pipeline: one row per application, status, next step. | `/offer`, `/job-apply` |
| `application/` | Template for one application folder: resume, cover letter, JD analysis, interview prep. | copied per role by `/make-resume` |
| `resume.css` | One-page Letter stylesheet shared by every resume. | you |

Per-role folders live next to these files as `YYYY-MM-DD-Company-Role-ReqID/`.

## Source of truth

`facts.md` is the only root. Everything else is derived from it and may only reword, select and order:

```
facts.md ──► blocks.md ──► <folder>/01-Resume.html, 02-Cover-Letter.md
         ├─► stories.md (STAR) ──► interview prep
         └─► answers.yaml (forms only; contact details live here, not in facts.md)
```

A new number goes into `facts.md` first (with its denominator and where it comes from), then into a block. `scripts/check-trace.py` enforces it: `export-pdf.sh` runs it on every export, and you can run it on the derived files at any time:

```bash
python scripts/check-trace.py career/blocks.md career/stories.md
```

`scripts/career-eval.py blocks career/` and `… outcomes career/` measure block selection and response rates from the same files (offline, no model calls).
