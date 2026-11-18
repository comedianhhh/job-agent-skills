"""Second backend for LinkedIn search: the Agent Reach CLI (`agent-reach linkedin jobs`).

Used only when the guest search fails with a *retryable* code (UPSTREAM_BROKEN, TIMEOUT).
A throttled guest search (RATE_LIMITED) is never retried through Agent Reach: LinkedIn is
throttling this machine, and a second route to the same site only makes that worse.

Agent Reach drives the user's own signed-in browser through OpenCLI, so it can answer
NEED_LOGIN; jobs-mcp passes that on and never logs in itself.

Off when `agent-reach` is not on PATH, or when JOBS_MCP_FALLBACK=0.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from typing import Any

from .boards import Job
from .result import (
    BAD_INPUT,
    NEED_LOGIN,
    NOT_FOUND,
    RATE_LIMITED,
    TIMEOUT,
    UPSTREAM_BROKEN,
    JobsError,
)

BACKEND = "agent-reach"
TIMEOUT_SECONDS = 150

# Agent Reach codes -> jobs-mcp codes. Anything unknown is UPSTREAM_BROKEN.
_CODES = {
    NEED_LOGIN: NEED_LOGIN,
    RATE_LIMITED: RATE_LIMITED,
    "PLATFORM_BLOCKED": RATE_LIMITED,
    NOT_FOUND: NOT_FOUND,
    BAD_INPUT: BAD_INPUT,
    TIMEOUT: TIMEOUT,
    "NEED_SETUP": UPSTREAM_BROKEN,
    "BUSY": UPSTREAM_BROKEN,
    UPSTREAM_BROKEN: UPSTREAM_BROKEN,
}


def find_agent_reach() -> str | None:
    """Path to the agent-reach executable, or None when the fallback is off."""
    if os.environ.get("JOBS_MCP_FALLBACK", "1") == "0":
        return None
    return shutil.which("agent-reach")


def run_agent_reach(argv: list[str], timeout: float) -> dict[str, Any]:
    """Run agent-reach and return its JSON envelope. Split out so tests can replace it."""
    try:
        p = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8", timeout=timeout)
    except subprocess.TimeoutExpired:
        raise JobsError(TIMEOUT, f"{BACKEND}: no answer in {timeout:.0f}s", source=BACKEND) from None
    except OSError as e:
        raise JobsError(UPSTREAM_BROKEN, f"{BACKEND}: could not start: {e}", source=BACKEND) from None
    lines = [ln for ln in p.stdout.splitlines() if ln.strip()]
    try:
        return json.loads(lines[-1])
    except (IndexError, json.JSONDecodeError):
        raise JobsError(
            UPSTREAM_BROKEN, f"{BACKEND}: no JSON on stdout (exit {p.returncode})", source=BACKEND
        ) from None


def _to_job(item: dict[str, Any]) -> Job | None:
    raw = item.get("raw") if isinstance(item.get("raw"), dict) else {}
    url = item.get("url") or raw.get("url") or ""
    m = re.search(r"/jobs/view/(?:[^/?]+-)?(\d+)", url)
    if not (item.get("title") and m):
        return None
    return Job(
        source="linkedin",
        board=BACKEND,
        id=m.group(1),
        title=str(item["title"]).strip(),
        company=str(raw.get("company") or item.get("author") or "").strip(),
        location=str(raw.get("location") or "").strip(),
        remote=None,
        url=f"https://www.linkedin.com/jobs/view/{m.group(1)}/",
        posted_at=item.get("published_at") or raw.get("posted_at") or raw.get("listed_at"),
        description=None,
        backend=BACKEND,
    )


def linkedin_jobs(exe: str, keywords: str, location: str, limit: int) -> list[Job]:
    """Search LinkedIn through Agent Reach. Raises JobsError on failure or an empty answer."""
    argv = [exe, "linkedin", "jobs", keywords, "--limit", str(max(1, limit))]
    if location:
        argv += ["--location", location]
    env = run_agent_reach(argv, TIMEOUT_SECONDS)
    if not env.get("ok"):
        e = env.get("error") or {}
        code = _CODES.get(str(e.get("code")), UPSTREAM_BROKEN)
        raise JobsError(code, f"{BACKEND}: {e.get('message') or 'failed'}", e.get("hint"), source=BACKEND)
    jobs = [j for j in (_to_job(i) for i in env.get("items") or []) if j]
    if not jobs:
        raise JobsError(UPSTREAM_BROKEN, f"{BACKEND}: answered with no usable postings", source=BACKEND)
    return jobs[:limit]
