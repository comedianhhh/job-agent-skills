# Weekly local eval run (scheduled task prompt)

Paste the prompt below into a new scheduled task in the Claude app. Suggested settings: title
"每周一：job-agent-skills 技能测试", schedule Mondays 08:00 (`0 8 * * 1`), folder
`C:\Users\qeeq\Documents\GitHub`. It uses the logged-in `claude` CLI, so it needs no secret.

---

Run the weekly behavioural evals for the job-agent-skills plugin on this machine, using the logged-in `claude` CLI (subscription). No API key or token is needed or wanted.

Repository: C:\Users\qeeq\Documents\GitHub\job-agent-skills

Rules:
- Do NOT switch branches, pull, commit, push, stash, or edit any tracked file. Run on whatever is checked out, and record which branch and commit that is (`git rev-parse --abbrev-ref HEAD`, `git log -1 --format="%h %s"`), plus whether the working tree has uncommitted changes (`git status --short`).
- Make sure ANTHROPIC_API_KEY is not set for the run, so it uses the CLI login.
- The only files you create are under evals/results/ (gitignored).

Steps:
1. In the repository, run (Git Bash):
   `env -u ANTHROPIC_API_KEY bash evals/run.sh --smoke --json evals/results/smoke-<today YYYY-MM-DD>.json`
   It first runs `python evals/validate.py`. If validation fails with "hard link under the plugin" in a .venv folder, rebuild that venv without hard links (`UV_LINK_MODE=copy uv sync --reinstall` inside that folder; for a venv without uv.lock, `UV_LINK_MODE=copy uv pip install --reinstall -e ".[dev]"`), then run step 1 once more. For any other validation failure, stop and report it.
   The run makes real model calls and can take 10–30 minutes. If it fails on authentication, stop and report: "claude CLI is not logged in — run `claude auth login`".
2. Read the JSON result: overall pass rate, cases passed / total, cost estimate (`costUsd`), and for every case that did not pass: its name, which graders failed, and a one-line reason from the grader output.
3. Write evals/results/SUMMARY-<today YYYY-MM-DD>.md with: branch + commit tested (and "uncommitted changes present" if so), overall result, a table | Case | Result | Failed graders | Reason |, the path of the HTML report the run printed, and a comparison with the previous SUMMARY-*.md in that folder if one exists (newly failing / newly passing cases).
4. Finish with a 3-line summary: pass rate (x/y cases), the newly failing cases (or "none"), and the report path. Do not try to fix failures; just report them.
