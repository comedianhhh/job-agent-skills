"""MCP tools: registration plus the filtering / dedup / error-collection logic of `scan`."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from jobs_mcp import boards, server


def test_all_tools_registered():
    names = {t.name for t in asyncio.run(server.mcp.list_tools())}
    assert names == {"list_board_jobs", "get_job", "linkedin_search", "scan"}


# ------------------------------------------------------------ list_board_jobs


def test_list_board_jobs_strips_descriptions(mock_http):
    out = server.list_board_jobs("ashby:cohere")
    assert len(out) == 3
    assert all(j["description"] == "" for j in out)  # never ship full text from the list call


def test_list_board_jobs_title_regex_and_limit(mock_http):
    out = server.list_board_jobs("ashby:cohere", title_regex="member of technical staff")
    assert [j["title"] for j in out] == [
        "Member of Technical Staff, Modeling",
        "Senior Member of Technical Staff, Multimodal AI",
    ]
    assert len(server.list_board_jobs("ashby:cohere", limit=1)) == 1


def test_list_board_jobs_bad_spec():
    with pytest.raises(ValueError):
        server.list_board_jobs("doordashcanada")


# -------------------------------------------------------------------- get_job


def test_get_job_greenhouse_hits_single_endpoint(mock_http):
    j = server.get_job("greenhouse:doordashcanada", "7345227")
    assert j["id"] == "7345227"
    assert j["description"]
    assert mock_http.requests[-1].url.path.endswith("/jobs/7345227")


def test_get_job_lever_scans_board(mock_http):
    j = server.get_job("lever:paytm", "86665c39-2182-4d69-8b8c-33eac104ec2b")
    assert j["title"].startswith("Accounts Payable")
    assert j["description"]


def test_get_job_not_found(mock_http):
    with pytest.raises(ValueError, match="not found"):
        server.get_job("ashby:cohere", "does-not-exist")


# ------------------------------------------------------------ linkedin_search


def test_linkedin_search_passes_through(mock_http):
    out = server.linkedin_search("backend engineer", "Toronto, Ontario, Canada", hours=12, limit=2)
    assert len(out) == 2
    assert out[0]["company"] == "RBC"
    assert mock_http.requests[0].url.params["f_TPR"] == f"r{12 * 3600}"


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

    def fetch(spec: str):
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
    assert res["errors"] == []
    assert res["scanned"] == 12
    assert res["count"] == 12
    assert {j["source"] for j in res["jobs"]} == {"greenhouse", "lever", "ashby", "linkedin"}
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
    assert [j["id"] for j in res["jobs"]] == ["1"]
    assert len(res["errors"]) == 3
    assert res["errors"][0].startswith("greenhouse:broken: boom")
    assert res["errors"][1].startswith("workday:bad:")
    assert res["errors"][2].startswith("linkedin {")


def test_scan_empty_inputs():
    assert server.scan() == {"count": 0, "scanned": 0, "jobs": [], "errors": []}
