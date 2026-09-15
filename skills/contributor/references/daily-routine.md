# `/contributor` daily routine example

For hosts that support scheduled runs (Claude Code `/schedule` or `/loop`). The host invokes on schedule; `/contributor` handles checking, candidate preparation, verification, and reporting within one run.

## Example prompt

```text
Run the daily open-source contribution routine with /contributor for GitHub user <username>.

Target roles: <e.g. Software Engineer II — backend; full-stack; AI agents>. Current targets are the companies in career/tracker.md.
Stack: <languages / frameworks you can credibly contribute in>.
Tracks: OSS owned by target companies; the ecosystems their JDs name; <your own niche>.

Each run: first a read-only check of existing PRs (CI, review, comments, merge). Then rotate through recently active repos with clear contribution rules and objectively verifiable docs / tests / examples / small code issues. Unmerged PRs do not block new candidates.

Prepare at most 2 independent candidates with local diffs; never lower the bar to hit the number. Check CONTRIBUTING, AGENTS.md, AI_POLICY.md, related issues, claim status, open/closed PRs, and recent main to avoid duplicates and stale issues.

Every fork, push, PR, comment, or review fix is an external write: show target repo, account, branch, files, full diff, verification result, PR title and body, one at a time, and wait for my explicit confirmation before executing.

End with: existing PR status, repos and candidates checked, PRs prepared or submitted, verification results, reasons anything was dropped, optional time / context estimate. Unmerged = "submitted / in collaboration"; merged = "merged"; "adopted" only if the project states it.
```

## Scheduling boundaries

- The skill creates no background process and guarantees no wake-up; run time and retries are host configuration.
- The host may persist target repos and the last run's result, but upstream status is re-checked every run.
- One confirmation never becomes a standing write authorisation for later runs; every PR and every update is confirmed again.
- "No safe candidate today" is a normal outcome; the report explains the filter, and no make-work change is produced.
