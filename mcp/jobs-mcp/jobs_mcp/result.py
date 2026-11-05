"""One result shape for every tool, and error codes an agent can branch on.

Every tool returns

    {schema_version, ok, items, count, backend, attempts, error, ...tool extras}

`ok` says whether `items` is usable. On failure `items` is empty and `error` is
`{code, message, hint, retryable}`: `code` is one of the constants below, `hint` is
one sentence telling the agent what to do next, and `retryable` says whether trying
again (or another backend) can help. Agents branch on `ok` and `error.code`; they
never need to parse an upstream traceback.

The split follows Agent Reach (`agent_reach/runtime/result.py`): only UPSTREAM_BROKEN
and TIMEOUT are worth another attempt; the rest are final for this call.
"""

from __future__ import annotations

import json
import re
from typing import Any

import httpx

SCHEMA_VERSION = 1

UPSTREAM_BROKEN = "UPSTREAM_BROKEN"
TIMEOUT = "TIMEOUT"
NOT_FOUND = "NOT_FOUND"
BAD_INPUT = "BAD_INPUT"
RATE_LIMITED = "RATE_LIMITED"
NEED_LOGIN = "NEED_LOGIN"

#: Another attempt — later, or through another backend — may succeed.
RETRYABLE_CODES = frozenset({UPSTREAM_BROKEN, TIMEOUT})
#: Retrying or switching backends cannot help; the agent (or the user) must change something.
FINAL_CODES = frozenset({NOT_FOUND, BAD_INPUT, RATE_LIMITED, NEED_LOGIN})

DEFAULT_HINTS = {
    UPSTREAM_BROKEN: (
        "The source failed on its side; carry on with the other sources and try this one again "
        "later, once — do not retry in a loop."
    ),
    TIMEOUT: "The source did not answer in time; try once more later with a smaller `limit`.",
    NOT_FOUND: (
        "Check the board token (from the careers-page URL) or the job id — the posting may have "
        "closed; do not retry the same arguments."
    ),
    BAD_INPUT: (
        "Fix the arguments: boards are 'greenhouse:<token>', 'lever:<company>' or 'ashby:<org>', "
        "and regexes must compile."
    ),
    RATE_LIMITED: (
        "The source is throttling this machine; stop calling it for at least an hour, do not switch "
        "backends, and continue with the other sources."
    ),
    NEED_LOGIN: (
        "This content is behind a login, which jobs-mcp never does: open the url in the user's own "
        "browser or ask them to paste the job description; never ask for their password."
    ),
}

_MAX_MESSAGE = 500


class JobsError(RuntimeError):
    """A failure with a code from this module. Subclasses RuntimeError for older callers."""

    def __init__(self, code: str, message: str, hint: str | None = None, *, source: str | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.hint = hint
        self.source = source

    @property
    def retryable(self) -> bool:
        return self.code in RETRYABLE_CODES

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "code": self.code,
            "message": self.message[:_MAX_MESSAGE],
            "hint": self.hint or DEFAULT_HINTS.get(self.code, ""),
            "retryable": self.retryable,
        }
        if self.source:
            d["source"] = self.source
        return d


def http_status_code(status: int) -> str:
    """Error code for an HTTP status from a job board. 999 is LinkedIn's bot wall."""
    if status == 404:
        return NOT_FOUND
    if status in (429, 999):
        return RATE_LIMITED
    if status in (400, 422):
        return BAD_INPUT
    return UPSTREAM_BROKEN


def classify(exc: BaseException, source: str | None = None) -> JobsError:
    """Map anything a board client raises to a JobsError."""
    if isinstance(exc, JobsError):
        if source and not exc.source:
            exc.source = source
        return exc
    where = f"{source}: " if source else ""
    if isinstance(exc, httpx.TimeoutException):
        return JobsError(TIMEOUT, f"{where}no answer in time", source=source)
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        return JobsError(http_status_code(status), f"{where}HTTP {status}", source=source)
    if isinstance(exc, httpx.TransportError):
        return JobsError(UPSTREAM_BROKEN, f"{where}network error: {exc}", source=source)
    if isinstance(exc, json.JSONDecodeError):  # a ValueError, but the server's fault
        return JobsError(UPSTREAM_BROKEN, f"{where}response was not JSON", source=source)
    if isinstance(exc, (ValueError, TypeError, re.error)):
        return JobsError(BAD_INPUT, f"{where}{exc}", source=source)
    return JobsError(UPSTREAM_BROKEN, f"{where}{exc or type(exc).__name__}", source=source)


def ok(
    items: list[dict[str, Any]],
    *,
    backend: str | None = None,
    attempts: list[dict[str, Any]] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "ok": True,
        "items": items,
        "count": len(items),
        "backend": backend,
        "attempts": attempts or [],
        "error": None,
        **extra,
    }


def fail(
    err: BaseException,
    *,
    attempts: list[dict[str, Any]] | None = None,
    source: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    e = classify(err, source)
    return {
        "schema_version": SCHEMA_VERSION,
        "ok": False,
        "items": [],
        "count": 0,
        "backend": None,
        "attempts": attempts or [],
        "error": e.to_dict(),
        **extra,
    }


def attempt(backend: str, err: JobsError | None = None, count: int | None = None) -> dict[str, Any]:
    """One entry of `attempts`: which backend was tried and how it went."""
    if err is None:
        return {"backend": backend, "ok": True, "count": count}
    return {"backend": backend, "ok": False, "code": err.code, "message": err.message[:_MAX_MESSAGE]}
