"""jobs-mcp — an MCP server that lets an agent scan public job boards.

Tools:
  list_board_jobs   one Greenhouse / Lever / Ashby board, all open roles
  get_job           full description for one posting
  linkedin_search   LinkedIn's unauthenticated job search (title/company/location/url only)
  scan              many boards + LinkedIn queries at once, filtered, deduplicated, optionally ranked

Every tool returns the envelope from `result.py`: {ok, items, count, backend, attempts, error}.

Run:  python -m jobs_mcp                       (stdio transport, for Claude Code etc.)
      python -m jobs_mcp --http [--port 8765]  (streamable HTTP on 127.0.0.1, for hosts
                                                that attach remote MCP servers, e.g. Rakazo)
"""

from __future__ import annotations

import re
from typing import Any

try:  # mcp >= 2.0
    from mcp.server.mcpserver import MCPServer
except ImportError:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP as MCPServer

from . import boards, rank
from .result import BAD_INPUT, NOT_FOUND, JobsError, attempt, classify, fail, ok

mcp = MCPServer(
    "jobs-mcp",
    instructions=(
        "Scan public job boards (Greenhouse, Lever, Ashby, SmartRecruiters, LinkedIn guest search). "
        "Board specs look like 'greenhouse:doordashcanada', 'lever:netflix', 'ashby:cohere', "
        "'smartrecruiters:Ubisoft2'. "
        "Every tool returns {ok, items, count, backend, attempts, error}; each item is "
        "{source, board, id, title, company, location, url, posted_at, backend}. When ok is false, "
        "error is {code, message, hint, retryable}: follow error.hint, and retry only when "
        "retryable is true (UPSTREAM_BROKEN, TIMEOUT). NOT_FOUND, BAD_INPUT, RATE_LIMITED and "
        "NEED_LOGIN are final. Never log in for the user."
    ),
)

_DEFAULT_EXCLUDE = r"\b(senior|sr\.?|staff|principal|lead|manager|director|head|intern|co-?op|vp)\b"


def _compile(pattern: str | None, name: str) -> re.Pattern[str] | None:
    if not pattern:
        return None
    try:
        return re.compile(pattern, re.I)
    except re.error as e:
        raise JobsError(BAD_INPUT, f"{name} does not compile: {e}") from None


def _backend_of(spec: str, jobs: list[boards.Job]) -> str:
    if jobs and jobs[0].get("backend"):
        return jobs[0]["backend"]
    return f"{spec.split(':', 1)[0].strip().lower()}-api"


# ------------------------------------------------------------ list_board_jobs


@mcp.tool()
def list_board_jobs(board: str, title_regex: str | None = None, limit: int = 200) -> dict[str, Any]:
    """List open jobs on one board. `board` is 'greenhouse:<token>', 'lever:<company>', 'ashby:<org>'
    or 'smartrecruiters:<company id>' (the id in jobs.smartrecruiters.com/<id>, e.g. Ubisoft2).
    `title_regex` (case-insensitive) keeps only matching titles. Jobs are in `items`."""
    try:
        rx = _compile(title_regex, "title_regex")
        jobs = boards.fetch_board(board)
    except Exception as e:
        return fail(e, source=board)
    if rx:
        jobs = [j for j in jobs if rx.search(j["title"])]
    items = [boards.to_public(j, max_desc=0) for j in jobs[:limit]]
    backend = _backend_of(board, jobs)
    return ok(items, backend=backend, attempts=[attempt(backend, count=len(items))])


# -------------------------------------------------------------------- get_job


@mcp.tool()
def get_job(board: str, job_id: str) -> dict[str, Any]:
    """Full posting (plain-text description) for one job; `items[0]` is that job.
    Greenhouse / Lever / Ashby / SmartRecruiters: `board` is the board spec. LinkedIn: `board` is
    'linkedin' and `job_id` the posting id or any linkedin.com job URL (read from the public page,
    no login)."""
    try:
        if board.strip().lower().split(":", 1)[0] == "linkedin":
            job = boards.linkedin_guest_job(job_id)
            return ok(
                [boards.to_public(job)], backend=job["backend"], attempts=[attempt(job["backend"], count=1)]
            )
        source, slug = boards.parse_board(board)
        if source == "greenhouse":
            job = boards.greenhouse_job(slug, job_id)
        elif source == "smartrecruiters":
            job = boards.smartrecruiters_job(slug, job_id)
        else:
            job = next((j for j in boards.fetch_board(board) if j["id"] == str(job_id)), None)
            if job is None:
                raise JobsError(NOT_FOUND, f"job {job_id} not found on {board}")
    except Exception as e:
        return fail(e, source=board)
    return ok([boards.to_public(job)], backend=job["backend"], attempts=[attempt(job["backend"], count=1)])


# ------------------------------------------------------------ linkedin_search


def _linkedin(
    keywords: str,
    location: str,
    hours: int,
    limit: int,
    remote_only: bool,
    warnings: list[str],
    attempts: list[dict[str, Any]],
) -> list[boards.Job]:
    """LinkedIn guest search. Partial results (a later page failed) are kept and noted in
    `warnings`. Raises JobsError when nothing came back."""
    partial: list[JobsError] = []
    try:
        jobs = boards.linkedin_guest_jobs(keywords, location, hours, limit, remote_only, failures=partial)
        if not jobs and partial:
            raise partial[0]
    except Exception as e:
        err = classify(e, "linkedin-guest")
        attempts.append(attempt("linkedin-guest", err))
        raise err from None
    attempts.append(attempt("linkedin-guest", count=len(jobs)))
    warnings.extend(f"partial result: {p.message}" for p in partial)
    return jobs


@mcp.tool()
def linkedin_search(
    keywords: str,
    location: str,
    hours: int = 24,
    limit: int = 100,
    remote_only: bool = False,
) -> dict[str, Any]:
    """LinkedIn job search: postings matching `keywords` in `location` from the last `hours`.
    Items have title / company / location / url / posted_at — no description (open the url for it).
    Uses LinkedIn's public guest search — no login, ever."""
    warnings: list[str] = []
    attempts: list[dict[str, Any]] = []
    try:
        jobs = _linkedin(keywords, location, hours, limit, remote_only, warnings, attempts)
    except Exception as e:
        return fail(e, attempts=attempts, source="linkedin", warnings=warnings)
    return ok(
        [boards.to_public(j) for j in jobs],
        backend=attempts[-1]["backend"],
        attempts=attempts,
        warnings=warnings,
    )


# ----------------------------------------------------------------------- scan


@mcp.tool()
def scan(
    boards_: list[str] | None = None,
    linkedin_queries: list[dict[str, str]] | None = None,
    hours: int = 24,
    include_regex: str | None = None,
    exclude_regex: str | None = _DEFAULT_EXCLUDE,
    location_regex: str | None = None,
    limit: int = 100,
    rank_query: str | None = None,
) -> dict[str, Any]:
    """Scan several sources at once and return one deduplicated, filtered list in `items`.

    boards_:          e.g. ["greenhouse:doordashcanada", "ashby:cohere", "lever:shopify"]
    linkedin_queries: e.g. [{"keywords": "backend engineer", "location": "Toronto, Ontario, Canada"}]
    hours:            keep postings newer than this (postings without a timestamp are kept)
    include_regex:    title must match (e.g. "engineer|developer")
    exclude_regex:    title must NOT match; default drops senior/staff/lead/manager/intern
    location_regex:   location must match (e.g. "Toronto|Canada|Remote")
    rank_query:       profile text (stack, domains, target role); when set, eligible postings are
                      ranked best-first by BM25 (+ dense embeddings if the `rank` extra is installed)
                      before `limit` applies, and each gets `match_score` / `match_terms`

    A failing source never fails the scan: it lands in `source_errors` as {source, code, message,
    hint, retryable} and `ok` stays true. `ok` is false only when every source failed.
    """
    try:
        inc = _compile(include_regex, "include_regex")
        exc = _compile(exclude_regex, "exclude_regex")
        loc = _compile(location_regex, "location_regex")
    except JobsError as e:
        return fail(e, scanned=0, jobs=[], errors=[_legacy_message(e)], source_errors=[e.to_dict()])

    found: list[boards.Job] = []
    source_errors: list[JobsError] = []
    warnings: list[str] = []
    attempts: list[dict[str, Any]] = []
    sources = 0
    for spec in boards_ or []:
        sources += 1
        try:
            # ranking needs descriptions; Greenhouse only sends them when asked
            got = boards.fetch_board(spec, with_content=bool(rank_query))
        except Exception as e:  # keep scanning other boards
            err = classify(e, spec)
            source_errors.append(err)
            attempts.append({"source": spec, **attempt(_backend_of(spec, []), err)})
            continue
        found.extend(got)
        attempts.append({"source": spec, **attempt(_backend_of(spec, got), count=len(got))})
    for q in linkedin_queries or []:
        sources += 1
        label = f"linkedin {q.get('keywords', '')!r} @ {q.get('location', '')!r}"
        q_attempts: list[dict[str, Any]] = []
        try:
            found.extend(
                _linkedin(
                    q.get("keywords", ""),
                    q.get("location", ""),
                    hours=hours,
                    limit=int(q.get("limit", 100)),
                    remote_only=bool(q.get("remote_only", False)),
                    warnings=warnings,
                    attempts=q_attempts,
                )
            )
        except Exception as e:
            err = classify(e)
            err.source = label
            source_errors.append(err)
        attempts.extend({"source": label, **a} for a in q_attempts)

    eligible: list[boards.Job] = []
    seen: set[str] = set()
    for j in found:
        key = j.get("url") or f"{j['source']}:{j['id']}"
        if key in seen:
            continue
        if not boards.newer_than(j, hours):
            continue
        if inc and not inc.search(j["title"]):
            continue
        if exc and exc.search(j["title"]):
            continue
        if loc and not loc.search(j.get("location", "")):
            continue
        seen.add(key)
        eligible.append(j)
        if not rank_query and len(eligible) >= limit:
            break

    extra: dict[str, Any] = {}
    if rank_query:
        ranked, extra["ranked_by"] = rank.rank_jobs(rank_query, list(eligible))
        out = [boards.to_public(j, max_desc=0) for j in ranked[:limit]]
    else:
        out = [boards.to_public(j, max_desc=0) for j in eligible]

    shared: dict[str, Any] = {
        "scanned": len(found),
        "jobs": out,  # same list as `items`, kept for callers written before the envelope
        "errors": [_legacy_message(e) for e in source_errors],  # strings, for the same callers
        "source_errors": [e.to_dict() for e in source_errors],
        "warnings": warnings,
        **extra,
    }
    if sources and len(source_errors) == sources:
        first = source_errors[0]
        summary = JobsError(first.code, f"all {sources} sources failed; first: {first.message}", first.hint)
        return fail(summary, attempts=attempts, **shared)
    return ok(out, attempts=attempts, **shared)


def _legacy_message(e: JobsError) -> str:
    """'<source>: <message> [CODE]' — the plain-string form `errors` has always carried."""
    msg = e.message
    if e.source and not msg.startswith(e.source):
        msg = f"{e.source}: {msg}"
    return f"{msg} [{e.code}]"


def main(argv: list[str] | None = None) -> None:
    import argparse

    parser = argparse.ArgumentParser(prog="jobs-mcp", description="MCP server over public job boards.")
    parser.add_argument("--http", action="store_true", help="serve streamable HTTP instead of stdio")
    parser.add_argument(
        "--host", default="127.0.0.1", help="bind address for --http (default: loopback only)"
    )
    parser.add_argument("--port", type=int, default=8765, help="port for --http (default: 8765)")
    args = parser.parse_args(argv)
    if not args.http:
        mcp.run()
        return
    # mcp 1.x reads host/port from settings; 2.x takes them as run() kwargs.
    try:
        mcp.run(transport="streamable-http", host=args.host, port=args.port)
    except TypeError:
        mcp.settings.host = args.host
        mcp.settings.port = args.port
        mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
