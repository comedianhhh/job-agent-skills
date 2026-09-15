"""Shared fixtures: every test runs against recorded HTTP responses, never the live boards.

`mock_http` swaps `boards._client` for an httpx client whose transport answers from
`tests/fixtures/`. Fixtures were recorded once from the real endpoints and trimmed to
three postings each. Tests can add or override routes with `mock_http.route(...)`.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import httpx
import pytest

from jobs_mcp import boards

FIXTURES = Path(__file__).parent / "fixtures"


def load_json(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def load_text(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


Handler = Callable[[httpx.Request], httpx.Response]


class MockHTTP:
    """Routes requests by (host, path-prefix) and records every request it sees."""

    def __init__(self) -> None:
        self.routes: list[tuple[str, str, Handler]] = []
        self.requests: list[httpx.Request] = []

    def route(self, host: str, path_prefix: str, handler: Handler | httpx.Response) -> None:
        h = handler if callable(handler) else (lambda _req, _r=handler: _r)
        # later routes win, so tests can override the defaults
        self.routes.insert(0, (host, path_prefix, h))

    def json(self, host: str, path_prefix: str, fixture: str, status: int = 200) -> None:
        self.route(host, path_prefix, httpx.Response(status, json=load_json(fixture)))

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        for host, prefix, handler in self.routes:
            if request.url.host == host and request.url.path.startswith(prefix):
                return handler(request)
        return httpx.Response(404, text=f"no fixture for {request.url}")

    def client(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self), headers={"User-Agent": "test"})


@pytest.fixture
def mock_http(monkeypatch: pytest.MonkeyPatch) -> MockHTTP:
    m = MockHTTP()
    m.json("boards-api.greenhouse.io", "/v1/boards/doordashcanada/jobs", "greenhouse_jobs.json")
    m.json(
        "boards-api.greenhouse.io", "/v1/boards/doordashcanada/jobs/", "greenhouse_job.json"
    )  # more specific, registered last so it wins
    m.json("api.lever.co", "/v0/postings/paytm", "lever_jobs.json")
    m.json("api.ashbyhq.com", "/posting-api/job-board/cohere", "ashby_jobs.json")

    page = load_text("linkedin_page.html")

    def linkedin(request: httpx.Request) -> httpx.Response:
        # first page has cards; any later page is empty so pagination stops
        if request.url.params.get("start", "0") == "0":
            return httpx.Response(200, text=page)
        return httpx.Response(200, text="")

    m.route("www.linkedin.com", "/jobs-guest/jobs/api/seeMoreJobPostings/search", linkedin)

    monkeypatch.setattr(boards, "_client", m.client)
    return m
