"""Public job-board clients: Greenhouse, Lever, Ashby, LinkedIn guest search.

Every function returns a list of normalised `Job` dicts so the MCP tools and the
`scan` aggregator can treat all sources alike. No API keys are needed — these are
the same endpoints the public career pages use.
"""

from __future__ import annotations

import html
import re
from datetime import datetime, timedelta, timezone
from typing import Any, TypedDict
from urllib.parse import quote_plus

import httpx

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)
TIMEOUT = httpx.Timeout(20.0)


class Job(TypedDict, total=False):
    source: str  # greenhouse | lever | ashby | linkedin
    board: str  # board token / company slug / org slug / "guest"
    id: str
    title: str
    company: str
    location: str
    remote: bool | None
    url: str
    posted_at: str | None  # ISO 8601 when the source provides it
    description: str | None  # plain text, only when fetched


def _client() -> httpx.Client:
    return httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT, follow_redirects=True)


def _strip_html(s: str | None) -> str | None:
    if not s:
        return None
    s = html.unescape(s)
    s = re.sub(r"<br\s*/?>|</p>|</li>|</div>|</h\d>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"[ \t]+\n", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


# ---------------------------------------------------------------- Greenhouse


def greenhouse_jobs(board_token: str, with_content: bool = False) -> list[Job]:
    """All open jobs on a Greenhouse board, e.g. board_token="doordashcanada"."""
    url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs"
    params = {"content": "true"} if with_content else None
    with _client() as c:
        r = c.get(url, params=params)
        r.raise_for_status()
        data = r.json()
    jobs: list[Job] = []
    for j in data.get("jobs", []):
        jobs.append(
            Job(
                source="greenhouse",
                board=board_token,
                id=str(j.get("id")),
                title=j.get("title", ""),
                company=board_token,
                location=(j.get("location") or {}).get("name", ""),
                remote=None,
                url=j.get("absolute_url", ""),
                posted_at=j.get("updated_at") or j.get("first_published"),
                description=_strip_html(j.get("content")) if with_content else None,
            )
        )
    return jobs


def greenhouse_job(board_token: str, job_id: str) -> Job:
    url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs/{job_id}"
    with _client() as c:
        r = c.get(url)
        r.raise_for_status()
        j = r.json()
    return Job(
        source="greenhouse",
        board=board_token,
        id=str(j.get("id")),
        title=j.get("title", ""),
        company=board_token,
        location=(j.get("location") or {}).get("name", ""),
        remote=None,
        url=j.get("absolute_url", ""),
        posted_at=j.get("updated_at"),
        description=_strip_html(j.get("content")),
    )


# --------------------------------------------------------------------- Lever


def lever_jobs(company: str) -> list[Job]:
    """All open postings for a Lever company slug, e.g. company="netflix"."""
    url = f"https://api.lever.co/v0/postings/{company}?mode=json"
    with _client() as c:
        r = c.get(url)
        r.raise_for_status()
        data = r.json()
    jobs: list[Job] = []
    for j in data:
        cats = j.get("categories") or {}
        created = j.get("createdAt")
        posted = datetime.fromtimestamp(created / 1000, tz=timezone.utc).isoformat() if created else None
        jobs.append(
            Job(
                source="lever",
                board=company,
                id=str(j.get("id")),
                title=j.get("text", ""),
                company=company,
                location=cats.get("location", ""),
                remote=(j.get("workplaceType") == "remote") if j.get("workplaceType") else None,
                url=j.get("hostedUrl", ""),
                posted_at=posted,
                description=_strip_html(j.get("descriptionPlain") or j.get("description")),
            )
        )
    return jobs


# --------------------------------------------------------------------- Ashby


def ashby_jobs(org: str) -> list[Job]:
    """All open postings on an Ashby job board, e.g. org="cohere"."""
    url = f"https://api.ashbyhq.com/posting-api/job-board/{org}"
    with _client() as c:
        r = c.get(url, params={"includeCompensation": "true"})
        r.raise_for_status()
        data = r.json()
    jobs: list[Job] = []
    for j in data.get("jobs", []):
        comp = j.get("compensation") or {}
        summary = comp.get("compensationTierSummary")
        desc = _strip_html(j.get("descriptionHtml")) or j.get("descriptionPlain")
        if summary and desc:
            desc = f"Compensation: {summary}\n\n{desc}"
        jobs.append(
            Job(
                source="ashby",
                board=org,
                id=str(j.get("id")),
                title=j.get("title", ""),
                company=org,
                location=j.get("location", ""),
                remote=j.get("isRemote"),
                url=j.get("jobUrl") or j.get("applyUrl", ""),
                posted_at=j.get("publishedAt"),
                description=desc,
            )
        )
    return jobs


# ------------------------------------------------------------- LinkedIn guest

_LI_TITLE = re.compile(r'<h3 class="base-search-card__title">\s*(.*?)\s*</h3>', re.S)
_LI_COMPANY = re.compile(r'<h4 class="base-search-card__subtitle">.*?>\s*(.*?)\s*</a>', re.S)
_LI_LOC = re.compile(r'<span class="job-search-card__location">\s*(.*?)\s*</span>', re.S)
_LI_URL = re.compile(r'<a class="base-card__full-link[^"]*"[^>]*href="([^"]+)"', re.S)
_LI_TIME = re.compile(r'<time[^>]*datetime="([^"]+)"', re.S)
_LI_ID = re.compile(r'data-entity-urn="urn:li:jobPosting:(\d+)"')


def linkedin_guest_jobs(
    keywords: str,
    location: str,
    hours: int = 24,
    limit: int = 50,
    remote_only: bool = False,
) -> list[Job]:
    """LinkedIn's unauthenticated job search (the same endpoint the public /jobs page uses).

    Returns title / company / location / url / posted date only — fetch the page for the
    description. Be gentle: this is HTML scraping of a public page, rate-limited by LinkedIn.
    """
    jobs: list[Job] = []
    seen: set[str] = set()
    start = 0
    with _client() as c:
        while len(jobs) < limit and start < 200:
            params = {
                "keywords": keywords,
                "location": location,
                "f_TPR": f"r{hours * 3600}",
                "start": start,
            }
            if remote_only:
                params["f_WT"] = "2"
            r = c.get(
                "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search",
                params=params,
            )
            if r.status_code != 200 or not r.text.strip():
                break
            cards = [x for x in re.split(r"<li(?:\s[^>]*)?>", r.text)[1:] if "jobPosting:" in x]
            if not cards:
                break
            for card in cards:
                m_id = _LI_ID.search(card)
                jid = m_id.group(1) if m_id else ""
                if not jid or jid in seen:
                    continue
                seen.add(jid)
                m_url = _LI_URL.search(card)
                url = html.unescape(m_url.group(1)).split("?")[0] if m_url else ""
                m_time = _LI_TIME.search(card)
                jobs.append(
                    Job(
                        source="linkedin",
                        board="guest",
                        id=jid,
                        title=_strip_html(_group(_LI_TITLE, card)) or "",
                        company=_strip_html(_group(_LI_COMPANY, card)) or "",
                        location=_strip_html(_group(_LI_LOC, card)) or "",
                        remote=None,
                        url=url,
                        posted_at=m_time.group(1) if m_time else None,
                        description=None,
                    )
                )
                if len(jobs) >= limit:
                    break
            start += 25
    return jobs


def _group(rx: re.Pattern[str], s: str) -> str | None:
    m = rx.search(s)
    return m.group(1) if m else None


# -------------------------------------------------------------------- helpers


def newer_than(job: Job, hours: int) -> bool:
    """True when the job has a timestamp within `hours`, or no timestamp at all (unknown → keep)."""
    ts = job.get("posted_at")
    if not ts:
        return True
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return True
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt >= datetime.now(timezone.utc) - timedelta(hours=hours)


def parse_board(spec: str) -> tuple[str, str]:
    """'greenhouse:doordashcanada' -> ('greenhouse', 'doordashcanada')."""
    if ":" not in spec:
        raise ValueError(f"board spec must be 'source:slug', got {spec!r}")
    source, slug = spec.split(":", 1)
    source = source.strip().lower()
    if source not in {"greenhouse", "lever", "ashby"}:
        raise ValueError(f"unknown source {source!r}; use greenhouse, lever or ashby")
    return source, slug.strip()


def fetch_board(spec: str) -> list[Job]:
    source, slug = parse_board(spec)
    if source == "greenhouse":
        return greenhouse_jobs(slug)
    if source == "lever":
        return lever_jobs(slug)
    return ashby_jobs(slug)


def job_search_url(source: str, slug: str) -> str:
    return {
        "greenhouse": f"https://boards.greenhouse.io/{slug}",
        "lever": f"https://jobs.lever.co/{slug}",
        "ashby": f"https://jobs.ashbyhq.com/{slug}",
    }[source]


def linkedin_encode(q: str) -> str:
    return quote_plus(q)


def to_public(job: Job, max_desc: int | None = None) -> dict[str, Any]:
    d: dict[str, Any] = dict(job)
    if max_desc is not None and d.get("description"):
        d["description"] = d["description"][:max_desc]
    return d
