# jobs-mcp

MCP server that lets an agent scan public job boards. No API keys — it uses the same endpoints the public career pages use.

## Tools

| Tool | Args | Returns |
|---|---|---|
| `list_board_jobs` | `board` (`greenhouse:<token>` / `lever:<company>` / `ashby:<org>` / `smartrecruiters:<company id>`, e.g. `smartrecruiters:Ubisoft2`), `title_regex?`, `limit?` | open jobs on one board |
| `get_job` | `board`, `job_id` | one posting with plain-text description (Ashby includes the compensation summary when published); `board: "linkedin"` with a posting id or any LinkedIn job URL reads LinkedIn's public job page |
| `linkedin_search` | `keywords`, `location`, `hours?`, `limit?`, `remote_only?` | LinkedIn guest search: title / company / location / url / posted date |
| `scan` | `boards_?`, `linkedin_queries?`, `hours?`, `include_regex?`, `exclude_regex?`, `location_regex?`, `limit?`, `rank_query?` | one deduplicated, filtered list across all sources, plus per-source `source_errors`; with `rank_query`, sorted best-first with `match_score` / `match_terms` |

Every job is `{source, board, id, title, company, location, remote, url, posted_at, description, backend}`, where `backend` is what served it: `greenhouse-api`, `lever-api`, `ashby-api` or `linkedin-guest`.

## Result shape

Every tool returns the same envelope, and never raises for a board-side problem — a bad token or a throttled LinkedIn is an answer the agent can act on, not an MCP error:

```json
{
  "schema_version": 1,
  "ok": true,
  "items": [{ "source": "ashby", "id": "…", "title": "…", "backend": "ashby-api" }],
  "count": 1,
  "backend": "ashby-api",
  "attempts": [{ "backend": "ashby-api", "ok": true, "count": 1 }],
  "error": null
}
```

On failure `ok` is `false`, `items` is empty, and `error` says what happened and what to do next:

```json
{ "ok": false, "items": [], "count": 0, "backend": null,
  "error": { "code": "NOT_FOUND", "message": "greenhouse:acme: HTTP 404", "source": "greenhouse:acme",
             "hint": "Check the board token (from the careers-page URL) or the job id — …", "retryable": false } }
```

| Code | Retryable | Meaning → what the hint tells the agent |
|---|---|---|
| `UPSTREAM_BROKEN` | yes | the source failed on its side (5xx, network, non-JSON) → carry on, try once later |
| `TIMEOUT` | yes | no answer in time → try once more later with a smaller `limit` |
| `NOT_FOUND` | no | board token or job id does not exist (HTTP 404, job closed) → fix the argument |
| `BAD_INPUT` | no | bad board spec or regex → fix the argument; nothing was fetched |
| `RATE_LIMITED` | no | HTTP 429 / LinkedIn 999 → leave that source alone for an hour; do not switch backends |
| `NEED_LOGIN` | no | the content sits behind a login → open the url in the user's own browser or ask them to paste the text; jobs-mcp never logs in |

Only retryable codes are worth another attempt. The split and the envelope follow [Agent Reach](https://github.com/Panniantong/Agent-Reach)'s `runtime/result.py`.

Tool-specific fields sit next to the envelope:

- `get_job`: `items[0]` is the posting.
- `linkedin_search`: `warnings` (e.g. a later page was throttled and the result is partial).
- `scan`: `scanned`, `source_errors` (one `{source, code, message, hint, retryable}` per failed board or LinkedIn query), `warnings`, `ranked_by` when ranking; `attempts` entries carry their `source`. A failing source never fails the scan — `ok` is `false` only when **every** source failed. For callers written before the envelope, `jobs` (same list as `items`) and `errors` (`"<source>: <message> [CODE]"` strings) are still returned.

## Run

```bash
uvx --from . jobs-mcp            # from this directory
# or
pip install -e . && jobs-mcp
```

MCP config:

```json
{ "mcpServers": { "jobs-mcp": { "command": "uvx", "args": ["--from", "/path/to/mcp/jobs-mcp", "jobs-mcp"] } } }
```

## Ranking

Filters decide what is *eligible*; `rank_query` decides what comes *first*. Pass profile text (stack, domains, target role) and `scan` ranks the eligible postings before `limit` applies:

- **BM25** over title (weighted ×3) + description — pure Python, always on.
- **Dense** (optional): `pip install -e ".[rank]"` adds `fastembed` with `BAAI/bge-small-en-v1.5` (ONNX, no torch, ~130 MB downloaded on first use). BM25 and cosine rankings are merged with Reciprocal Rank Fusion (k = 60), so the two score scales never need calibrating. `JOBS_MCP_DENSE=0` forces BM25 only; if the model fails to load, BM25 is used and `ranked_by` says so.

The result carries `ranked_by: "bm25" | "bm25+dense"`; each job carries `match_score` and `match_terms` (query terms found in the posting). Greenhouse boards are fetched with `content=true` when ranking, since its list endpoint omits descriptions otherwise. LinkedIn guest results have no description, so they rank on title alone.

## Develop

```bash
pip install -e ".[dev]"
ruff check . && ruff format --check .
pytest
```

Tests run against recorded responses in `tests/fixtures/` (one trimmed snapshot per source), so they never touch the live boards. CI (`.github/workflows/ci.yml`) runs lint + tests on Python 3.10 / 3.12 / 3.13 against both `mcp<2` and `mcp>=2`.

## Notes

- LinkedIn job details (`get_job(board="linkedin", ...)`) come from the same public, logged-out page anyone sees at `linkedin.com/jobs/view/<id>`: title, company, location, the seniority / employment-type box and the full description. That page gives only a relative date ("3 days ago"), so it leads the description and `posted_at` stays null. jobs-mcp never logs in; a login wall comes back as `NEED_LOGIN`.
- LinkedIn guest search is HTML from a public page and is rate-limited by LinkedIn; keep `limit` modest and do not loop it. A 429 / 999 that survives the built-in backoff comes back as `RATE_LIMITED`.
- `scan` keeps postings that carry no timestamp (Greenhouse `updated_at` is an update time, not a first-published time).
- The default `exclude_regex` drops senior / staff / principal / lead / manager / director / intern / co-op titles; pass `""` to disable.
- Requires Python 3.10+, `mcp>=1.10` (1.x and 2.x both work), `httpx`.
