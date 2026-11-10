"""Board clients: each source is parsed into the normalised Job shape."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest

from jobs_mcp import boards
from jobs_mcp.result import RATE_LIMITED, UPSTREAM_BROKEN, JobsError

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
    "backend",
}
DESCRIBED_KEYS = JOB_KEYS | {"integrity"}  # a fetched description carries its posting-guard report


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
    assert set(j) == DESCRIBED_KEYS
    assert j["integrity"]["verdict"] == "clean"  # real postings must not trip the guard
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
    assert set(j) == DESCRIBED_KEYS
    assert j["integrity"]["verdict"] == "clean"  # real postings must not trip the guard
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


# ----------------------------------------------------------- SmartRecruiters


def test_smartrecruiters_jobs_normalises(mock_http):
    jobs = boards.smartrecruiters_jobs("Ubisoft2")
    assert len(jobs) == 3
    j = jobs[0]
    assert set(j) == JOB_KEYS
    assert j["source"] == "smartrecruiters" and j["board"] == "Ubisoft2"
    assert j["company"] == "Ubisoft"
    assert j["id"] == "744000160212611"
    assert j["title"] == "UI Programmer"
    assert j["location"] == "Saguenay, QC, Canada"
    assert j["remote"] is False
    assert j["url"].startswith("https://jobs.smartrecruiters.com/Ubisoft2/744000160212611")
    assert j["posted_at"].startswith("20")
    assert j["description"] is None  # the list endpoint has no job ad
    assert jobs[2]["location"].startswith("Toronto")


def test_smartrecruiters_paginates_until_total(mock_http):
    page = {
        "content": [{"id": str(i), "name": f"Job {i}", "location": {}} for i in range(100)],
        "totalFound": 150,
    }
    rest = {"content": [{"id": f"b{i}", "name": "J", "location": {}} for i in range(50)], "totalFound": 150}

    def handler(request):
        return httpx.Response(200, json=page if request.url.params.get("offset") == "0" else rest)

    mock_http.route("api.smartrecruiters.com", "/v1/companies/big/postings", handler)
    jobs = boards.smartrecruiters_jobs("big")
    assert len(jobs) == 150
    assert [r.url.params["offset"] for r in mock_http.requests] == ["0", "100"]


def test_smartrecruiters_job_has_guarded_description(mock_http):
    j = boards.smartrecruiters_job("Ubisoft2", "744000160212611")
    assert set(j) == DESCRIBED_KEYS
    assert j["integrity"]["verdict"] == "clean"
    assert "user interface programmer" in j["description"].lower()
    assert "<" not in j["description"]
    assert j["url"] == "https://jobs.smartrecruiters.com/Ubisoft2/744000160212611-ui-programmer"


def test_smartrecruiters_job_missing_is_not_found(mock_http):
    mock_http.route("api.smartrecruiters.com", "/v1/companies/Ubisoft2/postings/999", httpx.Response(404))
    with pytest.raises(JobsError) as e:
        boards.smartrecruiters_job("Ubisoft2", "999")
    assert e.value.code == "NOT_FOUND"


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
    assert starts == ["0", "3"]  # advanced by the 3 cards on page one; page two was empty -> stop


def _li_card(jid: str) -> str:
    return (
        f'<li><div data-entity-urn="urn:li:jobPosting:{jid}">'
        f'<h3 class="base-search-card__title">Job {jid}</h3>'
        '<time class="job-search-card__listdate" datetime="2026-11-02"></time></div></li>'
    )


def test_linkedin_guest_pages_by_cards_returned(mock_http):
    # LinkedIn serves 10 cards per page; a fixed step of 25 used to skip 15 of every 25
    total = 23

    def ten_per_page(request: httpx.Request) -> httpx.Response:
        start = int(request.url.params["start"])
        return httpx.Response(
            200, text="".join(_li_card(str(i)) for i in range(start, min(start + 10, total)))
        )

    mock_http.route("www.linkedin.com", "/jobs-guest", ten_per_page)
    jobs = boards.linkedin_guest_jobs("x", "y", limit=100)
    assert [j["id"] for j in jobs] == [str(i) for i in range(total)]
    assert [r.url.params["start"] for r in mock_http.requests] == ["0", "10", "20", "23"]


def test_linkedin_guest_retries_throttled_page(mock_http):
    calls = []

    def throttle_then_ok(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(429, text="slow down")
        return httpx.Response(200, text=_li_card("1") if request.url.params["start"] == "0" else "")

    mock_http.route("www.linkedin.com", "/jobs-guest", throttle_then_ok)
    assert [j["id"] for j in boards.linkedin_guest_jobs("x", "y")] == ["1"]


def test_linkedin_guest_non_200_raises_when_nothing_collected(mock_http):
    mock_http.route("www.linkedin.com", "/jobs-guest", httpx.Response(429, text="slow down"))
    with pytest.raises(RuntimeError, match="HTTP 429") as info:  # JobsError is a RuntimeError
        boards.linkedin_guest_jobs("x", "y")
    assert info.value.code == RATE_LIMITED and not info.value.retryable


def test_linkedin_guest_5xx_is_retryable(mock_http):
    mock_http.route("www.linkedin.com", "/jobs-guest", httpx.Response(503, text="down"))
    with pytest.raises(JobsError) as info:
        boards.linkedin_guest_jobs("x", "y")
    assert info.value.code == UPSTREAM_BROKEN and info.value.retryable


def test_linkedin_guest_non_200_goes_to_errors_and_keeps_partial(mock_http):
    def first_ok_then_blocked(request: httpx.Request) -> httpx.Response:
        if request.url.params["start"] == "0":
            return httpx.Response(200, text=_li_card("1"))
        return httpx.Response(999, text="")

    mock_http.route("www.linkedin.com", "/jobs-guest", first_ok_then_blocked)
    errors: list[str] = []
    jobs = boards.linkedin_guest_jobs("x", "y", errors=errors)
    assert [j["id"] for j in jobs] == ["1"]
    assert len(errors) == 1 and "HTTP 999 at start=1, kept 1" in errors[0]


def test_linkedin_guest_partial_failure_is_typed(mock_http):
    def first_ok_then_blocked(request: httpx.Request) -> httpx.Response:
        if request.url.params["start"] == "0":
            return httpx.Response(200, text=_li_card("1"))
        return httpx.Response(999, text="")

    mock_http.route("www.linkedin.com", "/jobs-guest", first_ok_then_blocked)
    failures: list[JobsError] = []
    jobs = boards.linkedin_guest_jobs("x", "y", failures=failures)
    assert [j["backend"] for j in jobs] == ["linkedin-guest"]
    assert [f.code for f in failures] == [RATE_LIMITED]


@pytest.mark.parametrize(
    "spec, backend",
    [
        ("greenhouse:doordashcanada", "greenhouse-api"),
        ("lever:paytm", "lever-api"),
        ("ashby:cohere", "ashby-api"),
    ],
)
def test_board_jobs_record_backend(mock_http, spec, backend):
    assert {j["backend"] for j in boards.fetch_board(spec)} == {backend}


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
    assert boards.fetch_board("smartrecruiters:Ubisoft2")[0]["source"] == "smartrecruiters"


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
    # a bare date is a whole local day: yesterday's date is still inside a 24 h window
    yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    assert boards.newer_than(boards.Job(posted_at=yesterday), 24)
    old = (now - timedelta(days=3)).strftime("%Y-%m-%d")
    assert not boards.newer_than(boards.Job(posted_at=old), 24)


def test_job_search_url():
    assert boards.job_search_url("greenhouse", "x") == "https://boards.greenhouse.io/x"
    assert boards.job_search_url("lever", "x") == "https://jobs.lever.co/x"
    assert boards.job_search_url("ashby", "x") == "https://jobs.ashbyhq.com/x"
    assert boards.job_search_url("smartrecruiters", "x") == "https://jobs.smartrecruiters.com/x"


def test_to_public_truncates_description():
    j = boards.Job(id="1", description="abcdef")
    assert boards.to_public(j)["description"] == "abcdef"
    assert boards.to_public(j, max_desc=3)["description"] == "abc"
    assert boards.to_public(j, max_desc=0)["description"] == ""
    assert boards.to_public(boards.Job(id="1", description=None), max_desc=0)["description"] is None


# ------------------------------------------------------- LinkedIn job detail


@pytest.fixture
def li_detail(mock_http):
    page = (Path(__file__).parent / "fixtures" / "linkedin_job.html").read_text(encoding="utf-8")
    mock_http.route(
        "www.linkedin.com", "/jobs-guest/jobs/api/jobPosting/4012345678", httpx.Response(200, text=page)
    )
    return mock_http


def test_linkedin_guest_job_parses_public_page(li_detail):
    j = boards.linkedin_guest_job("4012345678")
    assert set(j) == DESCRIBED_KEYS
    assert j["integrity"]["verdict"] == "clean"  # real postings must not trip the guard
    assert (j["source"], j["board"], j["backend"]) == ("linkedin", "guest", "linkedin-guest")
    assert j["title"] == "Backend Engineer, Platform & APIs"
    assert j["company"] == "Acme Robotics"
    assert j["location"] == "Toronto, Ontario, Canada"
    assert j["url"] == "https://www.linkedin.com/jobs/view/4012345678"
    assert j["posted_at"] is None  # the page only says "3 days ago"
    desc = j["description"]
    assert desc.startswith("Posted: 3 days ago\nSeniority level: Entry level\nEmployment type: Full-time\n\n")
    assert "2+ years of Python and PostgreSQL" in desc and "Show more" not in desc
    assert li_detail.requests[-1].url.path == "/jobs-guest/jobs/api/jobPosting/4012345678"


@pytest.mark.parametrize(
    "target",
    [
        "4012345678",
        "https://ca.linkedin.com/jobs/view/backend-engineer-at-acme-robotics-4012345678?trk=x",
        "https://www.linkedin.com/jobs/view/4012345678/",
        "https://www.linkedin.com/jobs/search/?currentJobId=4012345678&keywords=python",
        "urn:li:jobPosting:4012345678",
    ],
)
def test_linkedin_job_id_accepts_ids_and_urls(target):
    assert boards.linkedin_job_id(target) == "4012345678"


@pytest.mark.parametrize("target", ["", "abc", "12", "https://www.linkedin.com/in/someone"])
def test_linkedin_job_id_rejects(target):
    with pytest.raises(JobsError) as info:
        boards.linkedin_job_id(target)
    assert info.value.code == "BAD_INPUT"


@pytest.mark.parametrize("status, code", [(404, "NOT_FOUND"), (429, RATE_LIMITED), (503, UPSTREAM_BROKEN)])
def test_linkedin_guest_job_http_errors(mock_http, status, code):
    mock_http.route("www.linkedin.com", "/jobs-guest/jobs/api/jobPosting/", httpx.Response(status, text=""))
    with pytest.raises(JobsError) as info:
        boards.linkedin_guest_job("4012345678")
    assert info.value.code == code


def test_linkedin_guest_job_authwall_is_need_login(mock_http):
    wall = '<html><body><a href="https://www.linkedin.com/authwall?trk=x">Sign in</a></body></html>'
    mock_http.route("www.linkedin.com", "/jobs-guest/jobs/api/jobPosting/", httpx.Response(200, text=wall))
    with pytest.raises(JobsError) as info:
        boards.linkedin_guest_job("4012345678")
    assert info.value.code == "NEED_LOGIN"


def test_linkedin_guest_job_unknown_layout_is_upstream_broken(mock_http):
    mock_http.route(
        "www.linkedin.com", "/jobs-guest/jobs/api/jobPosting/", httpx.Response(200, text="<p>?</p>")
    )
    with pytest.raises(JobsError) as info:
        boards.linkedin_guest_job("4012345678")
    assert info.value.code == UPSTREAM_BROKEN and "layout" in info.value.message
