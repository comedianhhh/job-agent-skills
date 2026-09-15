# Tracker web app

A web layer over the `career/` workspace. The markdown files stay the record; this adds a board you can drag, a scan page, and history.

```
web/
  api/   FastAPI  — reads/writes career/tracker.md, runs jobs-mcp scans, stores events + postings (Postgres or SQLite)
  app/   Next.js  — kanban board (@dnd-kit) and scan/triage page
```

## Run with Docker

```bash
cp .env.example .env            # set TRACKER_TOKEN (python -c "import secrets;print(secrets.token_urlsafe(32))") and CAREER_DIR
docker compose up --build -d
```

| Service | Port | Notes |
|---|---|---|
| `web` | 3000 | Next.js; the browser only talks to this. `/api/*` is proxied server-side to the api container |
| `api` | internal | FastAPI; `career/` is bind-mounted at `/career`; OpenAPI docs at `/docs` |
| `db` | internal | Postgres 16, volume `pgdata` |

Open http://localhost:3000, paste the token once (it is kept in the browser's localStorage), done.

## Auth

One shared secret, `TRACKER_TOKEN`. The API requires `Authorization: Bearer <token>` on every `/api/*` route except `/api/health` (constant-time compare, `401` + `WWW-Authenticate: Bearer` otherwise). The web app never sees the token server-side — it forwards the browser's header through its `/api/[...path]` proxy. If `TRACKER_TOKEN` is unset the API runs open and logs a warning; compose refuses to start without it.

This is single-user auth, not accounts. If you expose the app beyond localhost, put HTTPS in front (Caddy, Tailscale Serve, a reverse proxy) — the token travels in a header.

## Run without Docker

```bash
# API (SQLite file inside career/ unless DATABASE_URL is set; add TRACKER_TOKEN=... to lock it)
cd web/api && uv sync --extra dev
CAREER_DIR=/path/to/career uv run uvicorn --factory tracker_api.main:create_app --reload

# Web (proxies /api/* to API_URL, default http://localhost:8000)
cd web/app && npm install && npm run dev      # http://localhost:3000
```

`jobs-mcp` is installed from `../../mcp/jobs-mcp` as a path dependency, so the scan page and the `/offer` skill run the exact same code.

## What the API does to your files

- **`tracker.md`** — the first 8-column table is the pipeline (`Company | Role | Req | Location | Applied | Status | Next step | Folder`, header text can be anything). Rows get a stable id from the folder link. A status change rewrites only that cell on that line, keeping backtick style, bold, links, the prose around the table, and CRLF/LF as they were. New rows are appended after the last row. If `tracker.md` is missing but `TRACKER.md` exists, that is used.
- **`targets.yaml`** — read for `boards`, `linkedin`, `filters` (`hours`, `include_regex`, `exclude_regex`, `location_regex`). Never written.
- **`SCAN-<date>.md`** — new postings from a scan are appended in the `/offer` table format; postings already in the tracker (req id or folder contains the posting id) are skipped.

## Endpoints

| Method | Path | |
|---|---|---|
| GET | `/api/health` | public; reports whether auth is on |
| GET | `/api/auth` | 200 with a valid token, else 401 — the UI's probe |
| GET | `/api/tracker` | rows with `follow_up_due` (≥ 10 business days in `APPLIED`) and `ghost_candidate` flags |
| PATCH | `/api/tracker/{id}` | `status`, `next_step`, `applied`, `location`, `req`, optional `note` → event |
| POST | `/api/tracker` | new `DRAFT` row |
| GET | `/api/tracker/{id}/events`, `/api/events` | status history |
| GET | `/api/targets` | targets.yaml plus the effective jobs-mcp arguments |
| POST | `/api/scans` | run a scan (`hours`, `boards`, `linkedin`, regex overrides, `write_scan_file`) |
| GET | `/api/scans`, `/api/postings?triage=new\|shortlisted\|dismissed\|tracked` | history and results |
| PATCH | `/api/postings/{id}` | `triage`, `note` |
| POST | `/api/postings/{id}/track` | posting → `DRAFT` tracker row |

## Tests

```bash
cd web/api && uv run pytest        # tracker round-trip on a CRLF fixture with bold/links/backticks; API with jobs-mcp stubbed
cd web/app && npm run lint && npx tsc --noEmit && npm run build
```
