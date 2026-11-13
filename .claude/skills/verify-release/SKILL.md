---
name: verify-release
description: Maintainer check for job-agent-skills. `npm run verify` (~30 s) while working; `npm run verify:release` (~10 min, real model calls) before publishing to npm. Checks the exact tarball npm would ship, starts jobs-mcp from it, hits live job boards, runs the skill evals, and leaves evidence. Use when asked to "verify", "release", "publish", or "is this ready to ship".
---

# Verify a release

```bash
npm run verify           # ~30 s: offline tests, pack audit, jobs-mcp from the tarball, live boards
npm run verify:release   # + skill evals (~10 min on the claude.ai CLI login); the only run you may publish from
npm run verify -- --all  # also graph/ and web/api (they don't ship)
npm run verify -- --evals-json <file>   # re-score a saved eval result, no model calls
```

Verdicts: **PASS**, **FAIL** (a check failed), **BLOCKED** (a check couldn't run: network, a board gone, CLI not logged in). Only a `verify:release` PASS prints the publish command. Publish that exact tarball (`npm publish .verify/<run>/<file>.tgz`), not the working tree. Any later commit or version bump voids the PASS.

## What gates and what doesn't

| Gates the verdict | Reported only |
|---|---|
| Offline tests (CI's own), pack audit (required files, nothing private, < 2 MB, shipped files identical to the evaluated ones), jobs-mcp started from the tarball, live board answers | — |
| Eval **deterministic** graders: regex, tool_used, file_exists | Eval **llm-judge** graders: shown as NOTE. One smoke run of a small judge is too noisy to block a release. Read the notes, but don't rerun to "make it green" |

- A case whose deterministic graders fail is re-run once (the agent is nondeterministic). Failing twice is a FAIL.
- `evals/baseline.json` lists deterministic failures that are understood, with a reason, and shows them as KNOWN. Add a case only after reading its trace. Delete its line when verify says it passes now.
- An unreachable or missing board is BLOCKED, not FAIL. Swap the board in `LIVE_BOARDS`.

## Report

Give the verdict, the tarball and its sha256, the commit, the counts (KNOWN and NOTE included), eval cost and time, and the evidence path (`.verify/<run>/summary.md`). Name anything not checked: web/app's Next.js build is CI-only; graph/ and web/api are checked only with `--all`.

## Known traps

- GNU tar on Windows reads `C:\...` as a remote host, so the tarball is unpacked with relative paths.
- `npm run test:pi` uses the repo source, so it passes even when `files` drops jobs-mcp. Only the start from the tarball catches that.
- A PowerShell process query that has the run marker in its own command line matches itself, so the marker goes in through `VERIFY_MARK`.
- An llm judge sees only its rubric and the reply. A rubric that checks "no invented facts" must carry the sources: use a `fixture-sources` block (see evals/README.md).
