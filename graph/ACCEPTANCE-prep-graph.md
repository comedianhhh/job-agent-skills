# prep-graph — rules and acceptance

The model writes; code decides. Every rule below is a function in `gates.py` / `compact.py` with a test in
`tests/test_prep.py` or `tests/test_compact.py`. Done = all tests green, `ruff` clean, `npm run verify` green,
and one real Field24 run reaches a verdict.

| Rule | Code |
|---|---|
| The stage sentence must be in the email; REJECTED / OA / OFFER / APPLIED stop with no prep | `check_stage`, `stage_route` |
| A research claim is kept only if its quote is in the research text | `filter_brief` |
| Lead project is named in facts.md | `check_plan` |
| Every evidence quote is in facts.md or the candidate's answers; text after `TODO:` does not count | `check_plan`, `clean_quote`, `confirmed_only` |
| Every number in the pitch is in facts.md | `pitch_numbers` (reuses `scripts/check-trace.py`) |
| The pitch never talks itself down ("not familiar", "still learning") | `SELF_LIMITING` |
| The pitch is 170 words or fewer (about 60 seconds) | `MAX_PITCH_WORDS` |
| Every skill the posting names has a term in the plan (its `Skills:` line + a fixed skill list, raw posting only); a skill with nothing behind it becomes a gap | `jd_skills`, `uncovered_skills` |
| Failed checks go back to the model verbatim, at most 3 tries per round | `after_plan`, `MAX_PLANS` |
| Gaps are searched in the candidate's files before asking; found quotes must be in the named file; facts.md hits are filled in by code, other files need a confirm | `sort_evidence`, `fill_from_evidence` |
| New gaps from a re-plan are searched and asked too, at most 2 rounds | `after_plan`, `MAX_GAP_ROUNDS` |
| READY only with: stage verified, 0 problems, 0 gaps, at least 1 verified product claim | `readiness` |
| Compact: only REJECTED / GHOSTED folders, only the ones ticked; keep JD + sent resume (or the only PDF), delete what can be rebuilt, unknown files kept; one line in `archive.md`; tracker row stays | `compact.py` |
| A run never changes the role folder, `tracker.md` or `facts.md` (hash test) | `test_a_run_leaves_…_byte_identical` |

Still decided by the prompt only: which project is "closest to the product", concepts outside the fixed
skill list (e.g. "context management"), question quality, pitch tone, and the direct/partial label on found
evidence (a partial label is shown to the candidate, who confirms).

Out of scope: logging in to or scraping LinkedIn, sending email, committing or pushing without being asked.
