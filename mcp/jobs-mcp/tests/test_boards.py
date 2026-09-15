"""Board clients: each source is parsed into the normalised Job shape."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx
import pytest

from jobs_mcp import boards

JOB_KEYS = {
    "source",
    "board",
    "id",
    "title",
    "company",
    "location",
    "remote",
    "url",
    "posted_at",
    "description",
}


# ---------------------------------------------------------------- Greenhouse


def test_greenhouse_jobs_normalises(mock_http):
    jobs = boards.greenhouse_jobs("doordashcanada")
    assert len(jobs) == 3
    j = jobs[0]
    assert set(j) == JOB_KEYS
    assert j["source"] == "greenhouse"
    assert j["board"] == j["company"] == "doordashcanada"
    assert j["id"] == "7345227"
    assert j["title"] == "Account Manager, CPG Partnerships"
    assert j["location"] == "Toronto, ON"
    assert j["url"].startswith("https://")
    assert j["posted_at"] == "2026-09-14T15:52:36-04:00"
    assert j["remote"] is None
    assert j["description"] is None  # content not requested


def test_greenhouse_jobs_with_content_requests_content_and_strips_html(mock_http):
    jobs = boards.greenhouse_jobs("doordashcanada", with_content=True)
    req = mock_http.requests[-1]
    assert req.url.params["content"] == "true"
    desc = jobs[0]["description"]
    assert desc and "<" not in desc


def test_greenhouse_job_single(mock_http):
    j = boards.greenhouse_job("doordashcanada", "7345227")
    assert j["id"] == "7345227"
    assert j["description"] and "<" not in j["description"]
    assert mock_http.requests[-1].url.path == "/v1/boards/doordashcanada/jobs/7345227"


def test_greenhouse_http_error_raises(mock_http):
    mock_http.route("boards-api.greenhouse.io", "/v1/boards/nope", httpx.Response(404, json={"error": "no"}))
    with pytest.raises(httpx.HTTPStatusError):
        boards.greenhouse_jobs("nope")


# --------------------------------------------------------------------- Lever


def test_lever_jobs_normalises(mock_http):
    jobs = boards.lever_jobs("paytm")
    assert len(jobs) == 3
    j = jobs[0]
    assert set(j) == JOB_KEYS
    assert j["source"] == "lever"
    assert j["id"] == "9eed4fec-73f7-4114-a5d3-b2f689c92e8c"
    assert j["title"].startswith("Account Executive")
    assert j["location"] == "Dubai"
    assert j["remote"] is False  # workplaceType == "onsite"
    assert j["url"].startswith("https://jobs.lever.co/paytm/")
    assert j["description"] and "<" not in j["description"]


def test_lever_created_at_ms_becomes_iso_utc(mock_http):
    j = boards.lever_jobs("paytm")[0]
    assert j["posted_at"] == datetime.fromtimestamp(1783043640931 / 1000, tz=timezone.utc).isoformat()


def test_lever_remote_flag_from_workplace_type(mock_http):
    data = [
        {"id": "a", "text": "A", "categories": {}, "workplaceType": "remote"},
        {"id": "b", "text": "B", "categories": {}},
    ]
    mock_http.route("api.lever.co", "/v0/postings/x", httpx.Response(200, json=data))
    a, b = boards.lever_jobs("x")
    assert a["remote"] is True
    assert b["remote"] is None
    assert b["posted_at"] is None


# --------------------------------------------------------------------- Ashby


def test_ashby_jobs_normalises_and_prefixes_compensation(mock_http):
    jobs = boards.ashby_jobs("cohere")
    assert len(jobs) == 3
    j = jobs[0]
    assert set(j) == JOB_KEYS
    assert j["source"] == "ashby"
    assert j["title"] == "Member of Technical Staff, Modeling"
    assert j["remote"] is True
    assert j["description"].startswith("Compensation: CA$250K")
    assert mock_http.requests[-1].url.params["includeCompensation"] == "true"


def test_ashby_without_compensation_leaves_description_alone(mock_http):
    data = {"jobs": [{"id": "1", "title": "T", "descriptionHtml": "<p>hi</p>", "jobUrl": "u"}]}
    mock_http.route("api.ashbyhq.com", "/posting-api/job-board/plain", httpx.Response(200, json=data))
    (j,) = boards.ashby_jobs("plain")
    assert j["description"] == "hi"
    assert j["url"] == "u"


# ------------------------------------------------------------- LinkedIn guest


def test_linkedin_guest_parses_cards(mock_http):
    jobs = boards.linkedin_guest_jobs("backend engineer", "Toronto, Ontario, Canada", hours=24, limit=50)
    assert [j["id"] for j in jobs] == ["4458535812", "4456569369", "4467430868"]
    j = jobs[0]
    assert set(j) == JOB_KEYS
    assert j["source"] == "linkedin" and j["board"] == "guest"
    assert j["title"] == "Application Developer - Expert"
    assert j["company"] == "RBC"
    assert j["location"] == "Toronto, Ontario, Canada"
    assert j["url"] == "https://ca.linkedin.com/jobs/view/application-developer-expert-at-rbc-4458535812"
    assert j["posted_at"] == "2026-09-15"
    assert j["description"] is None


def test_linkedin_guest_query_params(mock_http):
    boards.linkedin_guest_jobs("backend engineer", "Toronto", hours=48, limit=2, remote_only=True)
    p = mock_http.requests[0].url.params
    assert p["keywords"] == "backend engineer"
    assert p["location"] == "Toronto"
    assert p["f_TPR"] == f"r{48 * 3600}"
    assert p["f_WT"] == "2"
    assert p["start"] == "0"


def test_linkedin_guest_respects_limit_and_stops_paging(mock_http):
    jobs = boards.linkedin_guest_jobs("x", "y", limit=2)
    assert len(jobs) == 2
    assert len(mock_http.requests) == 1  # limit reached on page one, no second page


def test_linkedin_guest_pages_until_empty(mock_http):
    boards.linkedin_guest_jobs("x", "y", limit=50)
    starts = [r.url.params["start"] for r in mock_http.requests]
    assert starts == ["0", "25"]  # page two was empty -> stop


def test_linkedin_guest_non_200_returns_what_it_has(mock_http):
    mock_http.route("www.linkedin.com", "/jobs-guest", httpx.Response(429, text="slow down"))
    assert boards.linkedin_guest_jobs("x", "y") == []


# -------------------------------------------------------------------- helpers


def test_strip_html():
    assert boards._strip_html(None) is None
    assert boards._strip_html("") is None
    out = boards._strip_html(
        "<p>Hello&nbsp;<b>world</b></p><ul><li>a</li><li>b</li></ul>\n\n\n\n<div>end</div>"
    )
    assert out == "Hello world\na\nb\n\nend"


@pytest.mark.parametrize(
    "spec, expected",
    [
        ("greenhouse:doordashcanada", ("greenhouse", "doordashcanada")),
        (" Lever : paytm ", ("lever", "paytm")),
        ("ashby:cohere", ("ashby", "cohere")),
        ("ashby:org:with:colons", ("ashby", "org:with:colons")),
    ],
)
def test_parse_board_ok(spec, expected):
    assert boards.parse_board(spec) == expected


@pytest.mark.parametrize("spec", ["doordashcanada", "workday:acme", ""])
def test_parse_board_rejects(spec):
    with pytest.raises(ValueError):
        boards.parse_board(spec)


def test_fetch_board_dispatches(mock_http):
    assert boards.fetch_board("greenhouse:doordashcanada")[0]["source"] == "greenhouse"
    assert boards.fetch_board("lever:paytm")[0]["source"] == "lever"
    assert boards.fetch_board("ashby:cohere")[0]["source"] == "ashby"


def test_newer_than():
    now = datetime.now(timezone.utc)
    fresh = boards.Job(posted_at=(now - timedelta(hours=1)).isoformat())
    stale = boards.Job(posted_at=(now - timedelta(hours=30)).isoformat())
    assert boards.newer_than(fresh, 24)
    assert not boards.newer_than(stale, 24)
    assert boards.newer_than(boards.Job(posted_at=None), 24)  # unknown -> keep
    assert boards.newer_than(boards.Job(posted_at="not a date"), 24)  # unparsable -> keep
    z = (now - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    assert boards.newer_than(boards.Job(posted_at=z), 24)  # trailing Z
    naive = (now - timedelta(hours=1)).replace(tzinfo=None).isoformat()
    assert boards.newer_than(boards.Job(posted_at=naive), 24)  # naive -> assumed UTC
    date_only = (now - timedelta(hours=1)).strftime("%Y-%m-%d")  # LinkedIn gives dates, not datetimes
    assert boards.newer_than(boards.Job(posted_at=date_only), 48)


def test_job_search_url():
    assert boards.job_search_url("greenhouse", "x") == "https://boards.greenhouse.io/x"
    assert boards.job_search_url("lever", "x") == "https://jobs.lever.co/x"
    assert boards.job_search_url("ashby", "x") == "https://jobs.ashbyhq.com/x"


def test_to_public_truncates_description():
    j = boards.Job(id="1", description="abcdef")
    assert boards.to_public(j)["description"] == "abcdef"
    assert boards.to_public(j, max_desc=3)["description"] == "abc"
    assert boards.to_public(j, max_desc=0)["description"] == ""
    assert boards.to_public(boards.Job(id="1", description=None), max_desc=0)["description"] is None
