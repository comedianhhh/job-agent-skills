"""Run a jobs-mcp scan from `career/targets.yaml`, persist postings, append the day's SCAN file.

jobs-mcp is imported as a library here (same code the MCP server exposes to the agent), so the
web app and `/offer` see identical results for identical targets.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import yaml
from jobs_mcp import server as jobs
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import Posting, Scan, utcnow
from .tracker import Row, Tracker

SCAN_HEADER = "| Company | Role | Location | Posted | URL | first-look GAP |\n|---|---|---|---|---|---|\n"


def load_targets(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"boards": [], "linkedin": [], "filters": {}}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {
        "boards": list(data.get("boards") or []),
        "linkedin": list(data.get("linkedin") or []),
        "filters": dict(data.get("filters") or {}),
    }


def scan_params(targets: dict[str, Any], overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    """Merge targets.yaml with per-request overrides into jobs-mcp `scan()` kwargs."""
    f = targets.get("filters", {})
    o = overrides or {}
    params: dict[str, Any] = {
        "boards_": o.get("boards") if o.get("boards") is not None else targets.get("boards", []),
        "linkedin_queries": o.get("linkedin")
        if o.get("linkedin") is not None
        else targets.get("linkedin", []),
        "hours": int(o.get("hours") or f.get("hours") or 24),
        "include_regex": o.get("include_regex", f.get("include_regex")),
        "exclude_regex": o.get("exclude_regex", f.get("exclude_regex", jobs._DEFAULT_EXCLUDE)),
        "location_regex": o.get("location_regex", f.get("location_regex")),
        "limit": int(o.get("limit") or 200),
    }
    # jobs-mcp treats "" as "no filter"; YAML users may leave the key blank
    for k in ("include_regex", "exclude_regex", "location_regex"):
        if params[k] == "":
            params[k] = None
    return params


def _tracked_row(job: dict[str, Any], rows: list[Row]) -> Row | None:
    ext = str(job.get("id") or "")
    url = job.get("url") or ""
    for r in rows:
        if ext and (ext in r.req or ext in r.folder_href):
            return r
        if url and url in r.next_step:
            return r
    return None


def run_scan(
    session: Session,
    tracker: Tracker,
    career_dir: Path,
    params: dict[str, Any],
    *,
    write_scan_file: bool = True,
) -> Scan:
    scan = Scan(params=params)
    session.add(scan)
    session.flush()

    result = jobs.scan(**params)
    rows = tracker.rows() if tracker.path.exists() else []
    now = utcnow()
    new_postings: list[Posting] = []

    for job in result["jobs"]:
        key = job.get("url") or f"{job['source']}:{job['id']}"
        existing = session.scalar(select(Posting).where(Posting.key == key))
        if existing:
            existing.last_seen = now
            existing.times_seen += 1
            existing.scan_id = scan.id
            continue
        p = Posting(
            key=key,
            source=job.get("source", ""),
            board=job.get("board", ""),
            external_id=str(job.get("id") or ""),
            title=job.get("title", ""),
            company=job.get("company", ""),
            location=job.get("location", ""),
            url=job.get("url", ""),
            posted_at=job.get("posted_at"),
            first_seen=now,
            last_seen=now,
            scan_id=scan.id,
        )
        tracked = _tracked_row(job, rows)
        if tracked:
            p.triage = "tracked"
            p.tracker_row_id = tracked.id
        session.add(p)
        new_postings.append(p)

    scan.scanned = result["scanned"]
    scan.matched = result["count"]
    scan.new = len(new_postings)
    scan.errors = result["errors"]
    scan.finished_at = utcnow()
    session.commit()

    if write_scan_file and new_postings:
        append_scan_file(career_dir, [p for p in new_postings if p.triage != "tracked"])
    return scan


def append_scan_file(career_dir: Path, postings: list[Posting], today: date | None = None) -> Path | None:
    """Same table `/offer` writes, so the agent and the web app share one scan log."""
    if not postings:
        return None
    today = today or date.today()
    path = career_dir / f"SCAN-{today.isoformat()}.md"
    fresh = not path.exists()
    with path.open("a", encoding="utf-8", newline="\n") as f:
        if fresh:
            f.write(f"# Scan — {today.isoformat()}\n\n{SCAN_HEADER}")
        for p in postings:
            posted = (p.posted_at or "")[:10]
            f.write(
                f"| {_cell(p.company)} | {_cell(p.title)} | {_cell(p.location)} | {posted} | {p.url} |  |\n"
            )
    return path


def _cell(s: str) -> str:
    return s.replace("|", "\\|").replace("\n", " ").strip()
