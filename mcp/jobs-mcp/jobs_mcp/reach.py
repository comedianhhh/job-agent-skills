"""Optional LinkedIn fallback through the Agent Reach CLI (github.com/Panniantong/Agent-Reach).

Used only when the guest-search path fails with a retryable error and `agent-reach` is
on PATH. Each command prints exactly one JSON envelope
`{ok, backend, items: [{title, url, author, published_at, text, raw}], error}`.

This module only ever runs the read-only `linkedin jobs` / `linkedin read` actions. It
never runs `agent-reach login`: when Reach answers NEED_LOGIN the error goes back to the
agent with a hint that the user has to log in themselves.

`JOBS_MCP_AGENT_REACH`: unset / `auto` → use `agent-reach` from PATH when present;
`0` / `off` → never use it; any other value → path to the executable.
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
ENV = "JOBS_MCP_AGENT_REACH"
JOBS_TIMEOUT = 150.0  # Reach's own linkedin jobs timeout is 120 s; leave room for start-up
READ_TIMEOUT = 120.0

LOGIN_HINT = (
    "LinkedIn needs a signed-in session for the agent-reach backend: ask the user to run "
    "`agent-reach login linkedin` themselves and sign in; never log in or handle their password."
)

_PASS_THROUGH = {NEED_LOGIN, RATE_LIMITED, NOT_FOUND, BAD_INPUT, TIMEOUT, UPSTREAM_BROKEN}
_JOB_ID = re.compile(r"/jobs/view/(?:[^/?#]*-)?(\d+)")


def executable() -> str | None:
    """Path to agent-reach if this fallback is enabled and installed, else None."""
    setting = os.environ.get(ENV, "").strip()
    if setting.lower() in {"0", "off", "false", "no"}:
        return None
    if setting and setting.lower() not in {"1", "on", "true", "auto"}:
        return setting if os.path.exists(setting) else shutil.which(setting)
    return shutil.which("agent-reach")


def available() -> bool:
    return executable() is not None


def run(args: list[str], timeout: float) -> list[dict[str, Any]]:
    """Run one agent-reach command and return its items, or raise JobsError."""
    exe = executable()
    if not exe:
        raise JobsError(UPSTREAM_BROKEN, "agent-reach is not installed", source=BACKEND)
    try:
        proc = subprocess.run(
            [exe, *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            stdin=subprocess.DEVNULL,  # never let it wait on a prompt
        )
    except subprocess.TimeoutExpired:
        raise JobsError(
            TIMEOUT, f"agent-reach did not answer within {timeout:.0f}s", source=BACKEND
        ) from None
    except OSError as e:
        raise JobsError(UPSTREAM_BROKEN, f"could not start agent-reach: {e}", source=BACKEND) from None

    env = _last_json_object(proc.stdout)
    if env is None:
        tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-1:] or [""]
        raise JobsError(
            UPSTREAM_BROKEN,
            f"agent-reach printed no JSON envelope (exit {proc.returncode}): {tail[0][:200]}",
            source=BACKEND,
        )
    if env.get("ok"):
        return list(env.get("items") or [])

    err = env.get("error") or {}
    upstream = str(err.get("code") or UPSTREAM_BROKEN)
    message = f"agent-reach {upstream}: {err.get('message') or 'failed'}"
    if upstream == NEED_LOGIN:
        raise JobsError(NEED_LOGIN, message, LOGIN_HINT, source=BACKEND)
    if upstream == "PLATFORM_BLOCKED":  # a verification wall: final, the user resolves it
        raise JobsError(RATE_LIMITED, message, err.get("hint"), source=BACKEND)
    code = upstream if upstream in _PASS_THROUGH else UPSTREAM_BROKEN  # NEED_SETUP, BUSY, ...
    raise JobsError(code, message, err.get("hint") if code == UPSTREAM_BROKEN else None, source=BACKEND)


def linkedin_jobs(keywords: str, location: str = "", limit: int = 25) -> list[Job]:
    args = ["linkedin", "jobs", keywords, "--limit", str(limit)]
    if location:
        args += ["--location", location]
    return [to_job(it) for it in run(args, JOBS_TIMEOUT)][:limit]


def linkedin_read(target: str) -> Job:
    """Full posting for a LinkedIn job URL or numeric id."""
    url = target if "linkedin.com" in target else f"https://www.linkedin.com/jobs/view/{target}"
    items = run(["linkedin", "read", url], READ_TIMEOUT)
    if not items:
        raise JobsError(NOT_FOUND, f"agent-reach found no posting at {url}", source=BACKEND)
    return to_job(items[0])


def to_job(item: dict[str, Any]) -> Job:
    """Reach item {title, url, author, published_at, text, raw} → jobs-mcp Job."""
    raw = item.get("raw") if isinstance(item.get("raw"), dict) else {}
    url = str(item.get("url") or raw.get("url") or "").split("?")[0]
    m = _JOB_ID.search(url)
    return Job(
        source="linkedin",
        board="agent-reach",
        id=m.group(1) if m else str(raw.get("id") or url),
        title=str(item.get("title") or raw.get("title") or ""),
        company=str(raw.get("company") or item.get("author") or ""),
        location=str(raw.get("location") or ""),
        remote=None,
        url=url,
        posted_at=item.get("published_at") or raw.get("listed") or raw.get("date") or None,
        description=item.get("text") or raw.get("description") or None,
        backend=BACKEND,
    )


def _last_json_object(stdout: str) -> dict[str, Any] | None:
    """Reach prints one envelope; tolerate stray log lines before it."""
    text = (stdout or "").strip()
    if not text:
        return None
    try:
        v = json.loads(text)
        return v if isinstance(v, dict) else None
    except json.JSONDecodeError:
        pass
    for line in reversed(text.splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                v = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(v, dict):
                return v
    return None
