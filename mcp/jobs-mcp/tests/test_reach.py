"""Optional agent-reach fallback for LinkedIn — with the CLI mocked, never the real one."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from jobs_mcp import reach, server
from jobs_mcp.result import NEED_LOGIN, RATE_LIMITED, TIMEOUT, UPSTREAM_BROKEN

TODAY = datetime.now(timezone.utc).date().isoformat()


def envelope(items=None, error=None) -> str:
    """What `agent-reach linkedin ...` prints: one JSON object."""
    return json.dumps(
        {
            "schema_version": 1,
            "ok": error is None,
            "channel": "linkedin",
            "action": "jobs",
            "backend": "opencli" if error is None else None,
            "items": items or [],
            "meta": {"elapsed_ms": 1, "attempts": []},
            "error": error,
        }
    )


def item(job_id: str, title: str = "Backend Engineer", published_at: str | None = TODAY) -> dict:
    return {
        "title": title,
        "url": f"https://www.linkedin.com/jobs/view/backend-engineer-at-acme-{job_id}?refId=x",
        "author": None,
        "published_at": published_at,
        "text": "Python, Postgres." if job_id == "detail" else None,
        "raw": {"company": "Acme", "location": "Toronto, ON"},
    }


class FakeReach:
    """Stands in for subprocess.run(['agent-reach', ...]); records every call."""

    def __init__(self) -> None:
        self.calls: list[list[str]] = []
        self.stdout = envelope([item("111"), item("222")])
        self.raise_: BaseException | None = None

    def __call__(self, cmd, **kw):
        self.calls.append(list(cmd))
        assert kw.get("timeout") and kw.get("stdin") is subprocess.DEVNULL
        if self.raise_:
            raise self.raise_
        return subprocess.CompletedProcess(cmd, 0, stdout=self.stdout, stderr="")


@pytest.fixture
def fake_reach(monkeypatch) -> FakeReach:
    fake = FakeReach()
    monkeypatch.setattr(reach, "executable", lambda: "agent-reach")
    monkeypatch.setattr(reach.subprocess, "run", fake)
    return fake


@pytest.fixture
def guest_down(mock_http):
    def down(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    mock_http.route("www.linkedin.com", "/jobs-guest", down)
    return mock_http


def _no_login_ever(fake: FakeReach) -> None:
    assert all("login" not in c for c in fake.calls)


# --------------------------------------------------------------- fallback path


def test_retryable_guest_failure_falls_back_to_agent_reach(guest_down, fake_reach):
    res = server.linkedin_search("backend engineer", "Toronto", limit=5)
    assert res["ok"] is True and res["error"] is None
    assert res["backend"] == "agent-reach"
    assert [(a["backend"], a["ok"]) for a in res["attempts"]] == [
        ("linkedin-guest", False),
        ("agent-reach", True),
    ]
    assert res["attempts"][0]["code"] == UPSTREAM_BROKEN
    j = res["items"][0]
    assert j["id"] == "111" and j["company"] == "Acme" and j["location"] == "Toronto, ON"
    assert j["url"] == "https://www.linkedin.com/jobs/view/backend-engineer-at-acme-111"
    assert {x["backend"] for x in res["items"]} == {"agent-reach"}
    assert fake_reach.calls == [
        ["agent-reach", "linkedin", "jobs", "backend engineer", "--limit", "5", "--location", "Toronto"]
    ]
    _no_login_ever(fake_reach)


def test_guest_5xx_after_retries_falls_back(mock_http, fake_reach):
    mock_http.route("www.linkedin.com", "/jobs-guest", httpx.Response(503, text="down"))
    res = server.linkedin_search("x", "y")
    assert res["ok"] and res["backend"] == "agent-reach"


def test_final_guest_error_does_not_fall_back(mock_http, fake_reach):
    mock_http.route("www.linkedin.com", "/jobs-guest", httpx.Response(429, text="slow down"))
    res = server.linkedin_search("x", "y")
    assert res["ok"] is False and res["error"]["code"] == RATE_LIMITED
    assert fake_reach.calls == []  # RATE_LIMITED is final: switching backends cannot help


def test_partial_guest_result_does_not_fall_back(mock_http, fake_reach):
    page = mock_http.routes[0][2]  # conftest registers LinkedIn last, so it is first: one page

    def first_then_503(request: httpx.Request) -> httpx.Response:
        if request.url.params.get("start", "0") == "0":
            return page(request)
        return httpx.Response(503, text="")

    mock_http.route("www.linkedin.com", "/jobs-guest", first_then_503)
    res = server.linkedin_search("x", "y", limit=50)
    assert res["ok"] and res["backend"] == "linkedin-guest" and res["count"] > 0
    assert res["warnings"] and "HTTP 503" in res["warnings"][0]
    assert fake_reach.calls == []


def test_need_login_is_returned_with_user_must_log_in_hint(guest_down, fake_reach):
    fake_reach.stdout = envelope(
        error={"code": "NEED_LOGIN", "message": "Not logged in to linkedin.com", "hint": "upstream hint"}
    )
    res = server.linkedin_search("x", "y")
    assert res["ok"] is False and res["items"] == []
    err = res["error"]
    assert err["code"] == NEED_LOGIN and err["retryable"] is False
    assert "agent-reach login linkedin" in err["hint"] and "themselves" in err["hint"]
    assert "never log in" in err["hint"]
    assert [(a["backend"], a.get("code")) for a in res["attempts"]] == [
        ("linkedin-guest", UPSTREAM_BROKEN),
        ("agent-reach", NEED_LOGIN),
    ]
    _no_login_ever(fake_reach)
    assert len(fake_reach.calls) == 1  # no second try after NEED_LOGIN


def test_fallback_timeout(guest_down, fake_reach):
    fake_reach.raise_ = subprocess.TimeoutExpired(["agent-reach"], 150)
    res = server.linkedin_search("x", "y")
    assert res["error"]["code"] == TIMEOUT and res["error"]["retryable"] is True


def test_fallback_garbage_output_is_upstream_broken(guest_down, fake_reach):
    fake_reach.stdout = "Traceback (most recent call last):\n  boom"
    res = server.linkedin_search("x", "y")
    assert res["error"]["code"] == UPSTREAM_BROKEN
    assert "no JSON envelope" in res["error"]["message"]


def test_fallback_tolerates_log_lines_before_envelope(guest_down, fake_reach):
    fake_reach.stdout = "starting browser...\n" + envelope([item("333")])
    res = server.linkedin_search("x", "y")
    assert [j["id"] for j in res["items"]] == ["333"]


def test_fallback_applies_hours_window(guest_down, fake_reach):
    old = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    fake_reach.stdout = envelope([item("1"), item("2", published_at=old), item("3", published_at=None)])
    res = server.linkedin_search("x", "y", hours=24)
    assert [j["id"] for j in res["items"]] == ["1", "3"]


def test_fallback_warns_that_remote_only_is_not_applied(guest_down, fake_reach):
    res = server.linkedin_search("x", "y", remote_only=True)
    assert res["ok"] and any("remote_only" in w for w in res["warnings"])


@pytest.mark.parametrize(
    "upstream, code",
    [("PLATFORM_BLOCKED", RATE_LIMITED), ("NEED_SETUP", UPSTREAM_BROKEN), ("BUSY", UPSTREAM_BROKEN)],
)
def test_reach_codes_map_onto_ours(guest_down, fake_reach, upstream, code):
    fake_reach.stdout = envelope(error={"code": upstream, "message": "m", "hint": "h"})
    assert server.linkedin_search("x", "y")["error"]["code"] == code


def test_scan_uses_fallback_and_records_backend(guest_down, fake_reach):
    res = server.scan(linkedin_queries=[{"keywords": "backend", "location": "Toronto"}], exclude_regex="")
    assert res["ok"] and res["source_errors"] == []
    assert {j["backend"] for j in res["items"]} == {"agent-reach"}
    assert [(a["source"], a["backend"], a["ok"]) for a in res["attempts"]] == [
        ("linkedin 'backend' @ 'Toronto'", "linkedin-guest", False),
        ("linkedin 'backend' @ 'Toronto'", "agent-reach", True),
    ]


def test_scan_need_login_lands_in_source_errors(guest_down, fake_reach, fake_boards_ok):
    fake_reach.stdout = envelope(error={"code": "NEED_LOGIN", "message": "Not logged in"})
    res = server.scan(boards_=["greenhouse:b"], linkedin_queries=[{"keywords": "x", "location": "y"}])
    assert res["ok"] is True  # the board still worked
    (e,) = res["source_errors"]
    assert e["code"] == NEED_LOGIN and "agent-reach login linkedin" in e["hint"]


@pytest.fixture
def fake_boards_ok(monkeypatch):
    from jobs_mcp import boards

    job = boards.Job(
        source="greenhouse", board="b", id="1", title="Engineer", company="b", location="", url="u",
        posted_at=None, description=None, backend="greenhouse-api",
    )  # fmt: skip
    monkeypatch.setattr(boards, "fetch_board", lambda spec, with_content=False: [job])


# ---------------------------------------------------------------- get_job read


def test_get_job_linkedin_reads_through_agent_reach(fake_reach):
    fake_reach.stdout = envelope([item("detail", title="Backend Engineer")])
    res = server.get_job("linkedin", "https://ca.linkedin.com/jobs/view/backend-engineer-at-acme-4012345678")
    assert res["ok"] and res["backend"] == "agent-reach"
    assert res["items"][0]["description"] == "Python, Postgres."
    assert fake_reach.calls[0][1:3] == ["linkedin", "read"]


def test_get_job_linkedin_bare_id_becomes_url(fake_reach):
    fake_reach.stdout = envelope([item("4012345678")])
    server.get_job("linkedin", "4012345678")
    assert fake_reach.calls[0][-1] == "https://www.linkedin.com/jobs/view/4012345678"


# ------------------------------------------------------------- PATH detection


def test_executable_respects_env(monkeypatch):
    monkeypatch.setattr(reach.shutil, "which", lambda name: f"/bin/{name}")
    monkeypatch.setenv(reach.ENV, "0")
    assert reach.executable() is None and not reach.available()
    monkeypatch.setenv(reach.ENV, "auto")
    assert reach.executable() == "/bin/agent-reach"
    monkeypatch.delenv(reach.ENV)
    assert reach.executable() == "/bin/agent-reach"


def test_not_on_path_means_no_fallback(monkeypatch, guest_down):
    monkeypatch.delenv(reach.ENV)
    monkeypatch.setattr(reach.shutil, "which", lambda name: None)
    calls = []
    monkeypatch.setattr(reach.subprocess, "run", lambda *a, **k: calls.append(a))
    res = server.linkedin_search("x", "y")
    assert res["error"]["code"] == UPSTREAM_BROKEN
    assert [a["backend"] for a in res["attempts"]] == ["linkedin-guest"] and calls == []
