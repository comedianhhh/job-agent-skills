"""LinkedIn fallback: guest search fails retryably -> Agent Reach; final codes never switch."""

from __future__ import annotations

from datetime import date

import httpx
import pytest
from test_server import assert_error, assert_ok

from jobs_mcp import fallback, server
from jobs_mcp.result import NEED_LOGIN, RATE_LIMITED, UPSTREAM_BROKEN

TODAY = date.today().isoformat()
REACH_OK = {
    "ok": True,
    "channel": "linkedin",
    "action": "jobs",
    "backend": "opencli",
    "items": [
        {
            "title": "Backend Engineer",
            "url": "https://www.linkedin.com/jobs/view/backend-engineer-at-acme-4100000001",
            "author": "Acme",
            "published_at": TODAY,
            "raw": {"location": "Toronto, ON"},
        },
        {
            "title": "Old Role",
            "url": "https://www.linkedin.com/jobs/view/4100000002/",
            "author": "Beta",
            "published_at": "2020-01-01",
            "raw": {},
        },
        {"title": "No URL", "url": None, "raw": {}},
    ],
    "error": None,
}


class FakeReach:
    def __init__(self, envelope: dict) -> None:
        self.envelope = envelope
        self.calls: list[list[str]] = []

    def __call__(self, argv: list[str], timeout: float) -> dict:
        self.calls.append(argv)
        return self.envelope


@pytest.fixture
def reach(monkeypatch: pytest.MonkeyPatch):
    def install(envelope: dict) -> FakeReach:
        fake = FakeReach(envelope)
        monkeypatch.setattr(fallback, "find_agent_reach", lambda: "agent-reach")
        monkeypatch.setattr(fallback, "run_agent_reach", fake)
        return fake

    return install


def _guest_down(mock_http) -> None:
    def down(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    mock_http.route("www.linkedin.com", "/jobs-guest", down)


def test_guest_down_switches_to_agent_reach(mock_http, reach):
    _guest_down(mock_http)
    fake = reach(REACH_OK)
    res = server.linkedin_search("backend engineer", "Toronto", hours=48)
    items = assert_ok(res)
    assert fake.calls == [
        ["agent-reach", "linkedin", "jobs", "backend engineer", "--limit", "100", "--location", "Toronto"]
    ]
    assert [(i["id"], i["company"], i["location"], i["backend"]) for i in items] == [
        ("4100000001", "Acme", "Toronto, ON", "agent-reach")
    ]  # the 2020 posting is outside `hours`; the item without a job URL is dropped
    assert res["backend"] == "agent-reach"
    assert [(a["backend"], a["ok"]) for a in res["attempts"]] == [
        ("linkedin-guest", False),
        ("agent-reach", True),
    ]
    assert res["attempts"][0]["code"] == UPSTREAM_BROKEN
    assert "came from agent-reach" in res["warnings"][0] and "1 dropped" in res["warnings"][0]


def test_rate_limited_never_switches(mock_http, reach):
    mock_http.route("www.linkedin.com", "/jobs-guest", httpx.Response(429, text="slow down"))
    fake = reach(REACH_OK)
    res = server.linkedin_search("x", "y")
    assert_error(res, RATE_LIMITED)
    assert fake.calls == []
    assert [a["backend"] for a in res["attempts"]] == ["linkedin-guest"]


def test_fallback_needs_login_keeps_guest_error(mock_http, reach):
    _guest_down(mock_http)
    reach(
        {
            "ok": False,
            "items": [],
            "error": {
                "code": "NEED_LOGIN",
                "message": "sign in to linkedin.com",
                "hint": "Run `agent-reach login linkedin`; never log in for the user.",
            },
        }
    )
    res = server.linkedin_search("x", "y")
    assert_error(res, UPSTREAM_BROKEN)  # the guest failure is what the caller asked about
    assert res["attempts"][1] == {
        "backend": "agent-reach",
        "ok": False,
        "code": NEED_LOGIN,
        "message": "agent-reach: sign in to linkedin.com",
    }


def test_unknown_reach_code_and_empty_answer_are_upstream_broken(reach):
    reach({"ok": False, "error": {"code": "SOMETHING_NEW", "message": "?"}})
    with pytest.raises(Exception) as e:
        fallback.linkedin_jobs("agent-reach", "x", "", 5)
    assert e.value.code == UPSTREAM_BROKEN
    reach({"ok": True, "items": [{"title": "t", "url": "https://example.com/x"}]})
    with pytest.raises(Exception) as e:
        fallback.linkedin_jobs("agent-reach", "x", "", 5)
    assert e.value.code == UPSTREAM_BROKEN and "no usable postings" in e.value.message


def test_scan_uses_fallback_per_query(mock_http, reach):
    _guest_down(mock_http)
    reach(REACH_OK)
    res = server.scan(linkedin_queries=[{"keywords": "backend", "location": "Toronto"}], hours=48)
    items = assert_ok(res)
    assert [i["backend"] for i in items] == ["agent-reach"]
    assert res["source_errors"] == []
    assert [a["backend"] for a in res["attempts"]] == ["linkedin-guest", "agent-reach"]


def test_env_switch_turns_fallback_off(monkeypatch):
    monkeypatch.undo()  # drop the autouse stub so the real find_agent_reach runs
    monkeypatch.setenv("JOBS_MCP_FALLBACK", "0")
    assert fallback.find_agent_reach() is None
