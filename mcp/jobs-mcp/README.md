# jobs-mcp

MCP server that lets an agent scan public job boards. No API keys — it uses the same endpoints the public career pages use.

## Tools

| Tool | Args | Returns |
|---|---|---|
| `list_board_jobs` | `board` (`greenhouse:<token>` / `lever:<company>` / `ashby:<org>`), `title_regex?`, `limit?` | open jobs on one board |
| `get_job` | `board`, `job_id` | one posting with plain-text description (Ashby includes the compensation summary when published) |
| `linkedin_search` | `keywords`, `location`, `hours?`, `limit?`, `remote_only?` | LinkedIn guest search: title / company / location / url / posted date |
| `scan` | `boards_?`, `linkedin_queries?`, `hours?`, `include_regex?`, `exclude_regex?`, `location_regex?`, `limit?` | one deduplicated, filtered list across all sources, plus per-source errors |

Every job is `{source, board, id, title, company, location, remote, url, posted_at, description}`.

Board tokens come from the careers-page URL: `boards.greenhouse.io/<token>`, `jobs.lever.co/<company>`, `jobs.ashbyhq.com/<org>`.

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

## Develop

```bash
pip install -e ".[dev]"
ruff check . && ruff format --check .
pytest
```

Tests run against recorded responses in `tests/fixtures/` (one trimmed snapshot per source), so they never touch the live boards. CI (`.github/workflows/ci.yml`) runs lint + tests on Python 3.10 / 3.12 / 3.13 against both `mcp<2` and `mcp>=2`.

## Notes

- LinkedIn guest search is HTML from a public page and is rate-limited by LinkedIn; keep `limit` modest and do not loop it.
- `scan` keeps postings that carry no timestamp (Greenhouse `updated_at` is an update time, not a first-published time).
- The default `exclude_regex` drops senior / staff / principal / lead / manager / director / intern / co-op titles; pass `""` to disable.
- Requires Python 3.10+, `mcp>=1.10` (1.x and 2.x both work), `httpx`.
