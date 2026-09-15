"""jobs-mcp — an MCP server that lets an agent scan public job boards.

Tools:
  list_board_jobs   one Greenhouse / Lever / Ashby board, all open roles
  get_job           full description for one posting
  linkedin_search   LinkedIn's unauthenticated job search (title/company/location/url only)
  scan              many boards + LinkedIn queries at once, filtered and deduplicated

Run:  python -m jobs_mcp            (stdio transport)
"""

from __future__ import annotations

import re
from typing import Any

try:  # mcp >= 2.0
    from mcp.server.mcpserver import MCPServer
except ImportError:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP as MCPServer

from . import boards

mcp = MCPServer(
    "jobs-mcp",
    instructions=(
        "Scan public job boards (Greenhouse, Lever, Ashby, LinkedIn guest search). "
        "Board specs look like 'greenhouse:doordashcanada', 'lever:netflix', 'ashby:cohere'. "
        "Results are normalised {source, board, id, title, company, location, url, posted_at}."
    ),
)

_DEFAULT_EXCLUDE = r"\b(senior|sr\.?|staff|principal|lead|manager|director|head|intern|co-?op|vp)\b"


@mcp.tool()
def list_board_jobs(board: str, title_regex: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
    """List open jobs on one board. `board` is 'greenhouse:<token>', 'lever:<company>' or 'ashby:<org>'.
    `title_regex` (case-insensitive) keeps only matching titles."""
    jobs = boards.fetch_board(board)
    if title_regex:
        rx = re.compile(title_regex, re.I)
        jobs = [j for j in jobs if rx.search(j["title"])]
    return [boards.to_public(j, max_desc=0) for j in jobs[:limit]]


@mcp.tool()
def get_job(board: str, job_id: str) -> dict[str, Any]:
    """Full posting (plain-text description) for one job on a Greenhouse / Lever / Ashby board."""
    source, slug = boards.parse_board(board)
    if source == "greenhouse":
        return boards.to_public(boards.greenhouse_job(slug, job_id))
    for j in boards.fetch_board(board):
        if j["id"] == str(job_id):
            return boards.to_public(j)
    raise ValueError(f"job {job_id} not found on {board}")


@mcp.tool()
def linkedin_search(
    keywords: str,
    location: str,
    hours: int = 24,
    limit: int = 50,
    remote_only: bool = False,
) -> list[dict[str, Any]]:
    """LinkedIn guest job search: postings matching `keywords` in `location` from the last `hours`.
    Returns title / company / location / url / posted_at — no description (open the url for it)."""
    return [boards.to_public(j) for j in boards.linkedin_guest_jobs(keywords, location, hours, limit, remote_only)]


@mcp.tool()
def scan(
    boards_: list[str] | None = None,
    linkedin_queries: list[dict[str, str]] | None = None,
    hours: int = 24,
    include_regex: str | None = None,
    exclude_regex: str | None = _DEFAULT_EXCLUDE,
    location_regex: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """Scan several sources at once and return one deduplicated, filtered list.

    boards_:          e.g. ["greenhouse:doordashcanada", "ashby:cohere", "lever:shopify"]
    linkedin_queries: e.g. [{"keywords": "backend engineer", "location": "Toronto, Ontario, Canada"}]
    hours:            keep postings newer than this (postings without a timestamp are kept)
    include_regex:    title must match (e.g. "engineer|developer")
    exclude_regex:    title must NOT match; default drops senior/staff/lead/manager/intern
    location_regex:   location must match (e.g. "Toronto|Canada|Remote")
    """
    found: list[boards.Job] = []
    errors: list[str] = []
    for spec in boards_ or []:
        try:
            found.extend(boards.fetch_board(spec))
        except Exception as e:  # keep scanning other boards
            errors.append(f"{spec}: {e}")
    for q in linkedin_queries or []:
        try:
            found.extend(
                boards.linkedin_guest_jobs(
                    q.get("keywords", ""), q.get("location", ""), hours=hours, limit=int(q.get("limit", 50))
                )
            )
        except Exception as e:
            errors.append(f"linkedin {q}: {e}")

    inc = re.compile(include_regex, re.I) if include_regex else None
    exc = re.compile(exclude_regex, re.I) if exclude_regex else None
    loc = re.compile(location_regex, re.I) if location_regex else None

    out: list[dict[str, Any]] = []
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
        out.append(boards.to_public(j, max_desc=0))
        if len(out) >= limit:
            break
    return {"count": len(out), "scanned": len(found), "jobs": out, "errors": errors}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
