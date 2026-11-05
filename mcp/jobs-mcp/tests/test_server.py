"""MCP tools: registration, the result envelope, and the filtering / dedup / error logic of `scan`."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from jobs_mcp import boards, server
from jobs_mcp.result import BAD_INPUT, NOT_FOUND, RATE_LIMITED, TIMEOUT, UPSTREAM_BROKEN

ENVELOPE_KEYS = {"schema_version", "ok", "items", "count", "backend", "attempts", "error"}


def assert_ok(res: dict) -> list[dict]:
    assert ENVELOPE_KEYS <= set(res)
    assert res["ok"] is True and res["error"] is None, res.get("error")
    assert res["count"] == len(res["items"])
    return res["items"]


def assert_error(res: dict, code: str) -> dict:
    assert ENVELOPE_KEYS <= set(res)
    assert res["ok"] is False and res["items"] == [] and res["count"] == 0
    err = res["error"]
    assert err["code"] == code, err
    assert err["hint"] and err["message"]
    assert err["retryable"] is (code in {UPSTREAM_BROKEN, TIMEOUT})
    return err


def test_all_tools_registered():
    names = {t.name for t in asyncio.run(server.mcp.list_tools())}
    assert names == {"list_board_jobs", "get_job", "linkedin_search", "scan"}


def test_tool_call_returns_envelope_not_mcp_error(mock_http):
    """A bad board is an answer the agent can act on, not an MCP-level isError."""
    out = asyncio.run(server.mcp.call_tool("list_board_jobs", {"board": "doordashcanada"}))
    text = str(out)
    assert "BAD_INPUT" in text and "hint" in text


# ------------------------------------------------------------ list_board_jobs


def test_list_board_jobs_strips_descriptions(mock_http):
    res = server.list_board_jobs("ashby:cohere")
    out = assert_ok(res)
    assert len(out) == 3
    assert all(j["description"] == "" for j in out)  # never ship full text from the list call
    assert res["backend"] == "ashby-api" and {j["backend"] for j in out} == {"ashby-api"}
    assert res["attempts"] == [{"backend": "ashby-api", "ok": True, "count": 3}]


def test_list_board_jobs_title_regex_and_limit(mock_http):
    out = assert_ok(server.list_board_jobs("ashby:cohere", title_regex="member of technical staff"))
    assert [j["title"] for j in out] == [
        "Member of Technical Staff, Modeling",
        "Senior Member of Technical Staff, Multimodal AI",
    ]
    assert server.list_board_jobs("ashby:cohere", limit=1)["count"] == 1


def test_list_board_jobs_bad_spec():
    err = assert_error(server.list_board_jobs("doordashcanada"), BAD_INPUT)
    assert "source:slug" in err["message"]
    assert err["source"] == "doordashcanada"


def test_list_board_jobs_bad_regex_is_bad_input(mock_http):
    err = assert_error(server.list_board_jobs("ashby:cohere", title_regex="("), BAD_INPUT)
    assert "title_regex" in err["message"]
    assert mock_http.requests == []  # rejected before any network call


def test_list_board_jobs_unknown_board_is_not_found(mock_http):
    err = assert_error(server.list_board_jobs("greenhouse:no-such-co"), NOT_FOUND)
    assert "HTTP 404" in err["message"]


@pytest.mark.parametrize(
    "status, code",
    [(429, RATE_LIMITED), (500, UPSTREAM_BROKEN), (502, UPSTREAM_BROKEN), (400, BAD_INPUT)],
)
def test_list_board_jobs_http_status_codes(mock_http, status, code):
    mock_http.route("api.ashbyhq.com", "/posting-api", httpx.Response(status, text="x"))
    assert_error(server.list_board_jobs("ashby:cohere"), code)


def test_list_board_jobs_timeout_is_retryable(mock_http):
    def slow(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    mock_http.route("api.lever.co", "/v0/postings", slow)
    err = assert_error(server.list_board_jobs("lever:paytm"), TIMEOUT)
    assert err["retryable"] is True


def test_list_board_jobs_non_json_is_upstream_broken(mock_http):
    mock_http.route("api.ashbyhq.com", "/posting-api", httpx.Response(200, text="<html>maintenance</html>"))
    assert_error(server.list_board_jobs("ashby:cohere"), UPSTREAM_BROKEN)


# -------------------------------------------------------------------- get_job


def test_get_job_greenhouse_hits_single_endpoint(mock_http):
    res = server.get_job("greenhouse:doordashcanada", "7345227")
    (j,) = assert_ok(res)
    assert j["id"] == "7345227"
    assert j["description"]
    assert res["backend"] == "greenhouse-api"
    assert mock_http.requests[-1].url.path.endswith("/jobs/7345227")


def test_get_job_lever_scans_board(mock_http):
    (j,) = assert_ok(server.get_job("lever:paytm", "86665c39-2182-4d69-8b8c-33eac104ec2b"))
    assert j["title"].startswith("Accounts Payable")
    assert j["description"]


def test_get_job_not_found(mock_http):
    err = assert_error(server.get_job("ashby:cohere", "does-not-exist"), NOT_FOUND)
    assert "not found" in err["message"]


def test_get_job_linkedin_without_agent_reach_says_what_to_do():
    err = assert_error(server.get_job("linkedin", "4012345678"), BAD_INPUT)
    assert "agent-reach" in err["message"]
    assert "paste" in err["hint"]


# ------------------------------------------------------------ linkedin_search


def test_linkedin_search_passes_through(mock_http):
    res = server.linkedin_search("backend engineer", "Toronto, Ontario, Canada", hours=12, limit=2)
    out = assert_ok(res)
    assert len(out) == 2
    assert out[0]["company"] == "RBC"
    assert res["backend"] == "linkedin-guest"
    assert res["attempts"] == [{"backend": "linkedin-guest", "ok": True, "count": 2}]
    assert mock_http.requests[0].url.params["f_TPR"] == f"r{12 * 3600}"


def test_linkedin_search_throttled_is_final(mock_http):
    mock_http.route("www.linkedin.com", "/jobs-guest", httpx.Response(429, text="slow down"))
    err = assert_error(server.linkedin_search("x", "y"), RATE_LIMITED)
    assert "HTTP 429" in err["message"] and "hour" in err["hint"]


def test_linkedin_search_network_down_without_fallback(mock_http):
    def down(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    mock_http.route("www.linkedin.com", "/jobs-guest", down)
    res = server.linkedin_search("x", "y")
    assert_error(res, UPSTREAM_BROKEN)
    assert [a["backend"] for a in res["attempts"]] == ["linkedin-guest"]


# ----------------------------------------------------------------------- scan


def _fresh(**kw) -> boards.Job:
    base = boards.Job(
        source="greenhouse",
        board="b",
        id="1",
        title="Software Engineer",
        company="b",
        location="Toronto, ON",
        remote=None,
        url="https://x/1",
        posted_at=(datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
        description="long text",
    )
    base.update(kw)
    return base


@pytest.fixture
def fake_boards(monkeypatch):
    """Replace fetch_board with an in-memory table so scan's logic is tested in isolation."""
    table: dict[str, list[boards.Job] | Exception] = {}

    def fetch(spec: str, with_content: bool = False):
        v = table[spec]
        if isinstance(v, Exception):
            raise v
        return v

    monkeypatch.setattr(boards, "fetch_board", fetch)
    return table


def test_scan_end_to_end_with_fixtures(mock_http):
    res = server.scan(
        boards_=["greenhouse:doordashcanada", "lever:paytm", "ashby:cohere"],
        linkedin_queries=[{"keywords": "backend engineer", "location": "Toronto, Ontario, Canada"}],
        hours=24 * 365 * 5,  # fixtures are a snapshot; don't let the clock drop them
        exclude_regex="",
    )
    assert_ok(res)
    assert res["errors"] == [] and res["source_errors"] == []
    assert res["items"] == res["jobs"]
    assert res["scanned"] == 12
    assert res["count"] == 12
    assert {j["source"] for j in res["jobs"]} == {"greenhouse", "lever", "ashby", "linkedin"}
    assert {j["backend"] for j in res["jobs"]} == {
        "greenhouse-api",
        "lever-api",
        "ashby-api",
        "linkedin-guest",
    }
    assert [a["ok"] for a in res["attempts"]] == [True] * 4
    assert all(not j["description"] for j in res["jobs"])


def test_scan_default_exclude_drops_senior_titles(fake_boards):
    fake_boards["greenhouse:b"] = [
        _fresh(id="1", title="Software Engineer", url="u1"),
        _fresh(id="2", title="Senior Software Engineer", url="u2"),
        _fresh(id="3", title="Sr. Backend Developer", url="u3"),
        _fresh(id="4", title="Engineering Manager", url="u4"),
        _fresh(id="5", title="Software Engineer Intern", url="u5"),
        _fresh(id="6", title="Co-op Developer", url="u6"),
        _fresh(id="7", title="Staff Engineer", url="u7"),
    ]
    res = server.scan(boards_=["greenhouse:b"])
    assert [j["id"] for j in res["jobs"]] == ["1"]
    assert res["scanned"] == 7 and res["count"] == 1


def test_scan_exclude_can_be_disabled(fake_boards):
    fake_boards["greenhouse:b"] = [_fresh(id="2", title="Senior Software Engineer")]
    assert server.scan(boards_=["greenhouse:b"], exclude_regex="")["count"] == 1
    assert server.scan(boards_=["greenhouse:b"], exclude_regex=None)["count"] == 1


def test_scan_include_and_location_filters(fake_boards):
    fake_boards["greenhouse:b"] = [
        _fresh(id="1", title="Backend Engineer", location="Toronto, ON", url="u1"),
        _fresh(id="2", title="Backend Engineer", location="Austin, TX", url="u2"),
        _fresh(id="3", title="Product Designer", location="Toronto, ON", url="u3"),
    ]
    res = server.scan(boards_=["greenhouse:b"], include_regex="engineer", location_regex="toronto|remote")
    assert [j["id"] for j in res["jobs"]] == ["1"]


def test_scan_drops_stale_keeps_undated(fake_boards):
    old = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
    fake_boards["greenhouse:b"] = [
        _fresh(id="1", url="u1"),
        _fresh(id="2", url="u2", posted_at=old),
        _fresh(id="3", url="u3", posted_at=None),
    ]
    res = server.scan(boards_=["greenhouse:b"], hours=24)
    assert [j["id"] for j in res["jobs"]] == ["1", "3"]


def test_scan_dedupes_by_url_then_source_id(fake_boards):
    fake_boards["greenhouse:a"] = [_fresh(id="1", url="https://same"), _fresh(id="2", url="https://same")]
    fake_boards["greenhouse:b"] = [_fresh(id="9", url=""), _fresh(id="9", url="")]
    res = server.scan(boards_=["greenhouse:a", "greenhouse:b"])
    assert res["scanned"] == 4
    assert [(j["id"], j["url"]) for j in res["jobs"]] == [("1", "https://same"), ("9", "")]


def test_scan_limit(fake_boards):
    fake_boards["greenhouse:b"] = [_fresh(id=str(i), url=f"u{i}") for i in range(10)]
    res = server.scan(boards_=["greenhouse:b"], limit=3)
    assert res["count"] == 3 and res["scanned"] == 10


def test_scan_collects_errors_and_keeps_going(fake_boards, mock_http):
    def raise_connect(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    fake_boards["greenhouse:ok"] = [_fresh(id="1", url="u1")]
    fake_boards["greenhouse:broken"] = RuntimeError("boom")
    fake_boards["workday:bad"] = ValueError("unknown source 'workday'")
    mock_http.route("www.linkedin.com", "/jobs-guest", raise_connect)
    res = server.scan(
        boards_=["greenhouse:broken", "greenhouse:ok", "workday:bad"],
        linkedin_queries=[{"keywords": "x", "location": "y"}],
    )
    assert_ok(res)  # one source worked, so the scan as a whole is usable
    assert [j["id"] for j in res["jobs"]] == ["1"]
    assert len(res["errors"]) == 3
    assert res["errors"][0].startswith("greenhouse:broken: boom")
    assert res["errors"][1].startswith("workday:bad:")
    assert res["errors"][2].startswith("linkedin 'x' @ 'y'")
    codes = [(e["source"], e["code"], e["retryable"]) for e in res["source_errors"]]
    assert codes == [
        ("greenhouse:broken", UPSTREAM_BROKEN, True),
        ("workday:bad", BAD_INPUT, False),
        ("linkedin 'x' @ 'y'", UPSTREAM_BROKEN, True),
    ]
    assert all(e["hint"] for e in res["source_errors"])


def test_scan_passes_remote_only_and_reports_throttling(mock_http):
    mock_http.route("www.linkedin.com", "/jobs-guest", httpx.Response(429, text="slow down"))
    res = server.scan(linkedin_queries=[{"keywords": "x", "location": "y", "remote_only": True}])
    assert mock_http.requests[0].url.params["f_WT"] == "2"
    assert len(res["errors"]) == 1 and "HTTP 429" in res["errors"][0]
    assert_error(res, RATE_LIMITED)  # the only source failed
    assert res["source_errors"][0]["code"] == RATE_LIMITED


def test_scan_all_sources_failed_is_not_ok(fake_boards):
    fake_boards["greenhouse:a"] = RuntimeError("boom")
    fake_boards["greenhouse:b"] = RuntimeError("bang")
    res = server.scan(boards_=["greenhouse:a", "greenhouse:b"])
    err = assert_error(res, UPSTREAM_BROKEN)
    assert "all 2 sources failed" in err["message"]
    assert len(res["source_errors"]) == 2 and res["jobs"] == []


def test_scan_bad_regex_fails_before_fetching(fake_boards):
    fake_boards["greenhouse:b"] = [_fresh()]
    res = server.scan(boards_=["greenhouse:b"], include_regex="[")
    assert_error(res, BAD_INPUT)
    assert res["jobs"] == [] and res["errors"] and res["scanned"] == 0


def test_scan_empty_inputs():
    res = server.scan()
    assert assert_ok(res) == []
    assert {k: res[k] for k in ("count", "scanned", "jobs", "errors")} == {
        "count": 0,
        "scanned": 0,
        "jobs": [],
        "errors": [],
    }


# ------------------------------------------------------------------ ranking


def test_scan_rank_query_orders_by_relevance_before_limit(fake_boards, monkeypatch):
    monkeypatch.setenv("JOBS_MCP_DENSE", "0")
    fake_boards["greenhouse:b"] = [
        _fresh(id="1", url="u1", title="Software Engineer", description="Java billing, Spring, Oracle."),
        _fresh(id="2", url="u2", title="Software Engineer", description="Unity C# gameplay."),
        _fresh(id="3", url="u3", title="Agents Engineer", description="Python LLM agents, MCP, evals."),
    ]
    res = server.scan(boards_=["greenhouse:b"], rank_query="Python LLM agents MCP evals", limit=2)
    assert res["ranked_by"] == "bm25"
    assert res["count"] == 2
    top = res["jobs"][0]
    assert top["id"] == "3"  # last on the board, first after ranking: limit applies after ranking
    assert {"python", "llm", "mcp", "evals"} <= set(top["match_terms"])
    assert top["match_score"] > res["jobs"][1]["match_score"]
    assert all(not j["description"] for j in res["jobs"])  # ranked on the text, text still not shipped


def test_scan_without_rank_query_keeps_board_order_and_shape(fake_boards):
    fake_boards["greenhouse:b"] = [_fresh(id=str(i), url=f"u{i}") for i in range(3)]
    res = server.scan(boards_=["greenhouse:b"])
    assert "ranked_by" not in res
    assert [j["id"] for j in res["jobs"]] == ["0", "1", "2"]
    assert "match_score" not in res["jobs"][0]


def test_scan_rank_query_fetches_greenhouse_content(mock_http, monkeypatch):
    monkeypatch.setenv("JOBS_MCP_DENSE", "0")
    server.scan(boards_=["greenhouse:doordashcanada"], hours=24 * 365 * 5, exclude_regex="", rank_query="x")
    assert mock_http.requests[0].url.params.get("content") == "true"
