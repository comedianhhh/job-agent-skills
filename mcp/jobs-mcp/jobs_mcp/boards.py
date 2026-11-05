"""Public job-board clients: Greenhouse, Lever, Ashby, LinkedIn guest search.

Every function returns a list of normalised `Job` dicts so the MCP tools and the
`scan` aggregator can treat all sources alike. No API keys are needed — these are
the same endpoints the public career pages use.
"""

from __future__ import annotations

import html
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any, TypedDict
from urllib.parse import quote_plus

import httpx

from .result import BAD_INPUT, NEED_LOGIN, NOT_FOUND, UPSTREAM_BROKEN, JobsError, http_status_code

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)
TIMEOUT = httpx.Timeout(20.0)
# LinkedIn guest search: pause between page requests, and once before retrying a throttled one.
LI_PAGE_DELAY = 2.0
LI_RETRY_DELAYS = (10.0, 30.0)  # waits before each retry of a throttled page
LI_MAX_START = 1000  # the guest endpoint stops returning cards around here


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
    backend: str  # what served it: greenhouse-api | lever-api | ashby-api | linkedin-guest


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
                backend="greenhouse-api",
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
        backend="greenhouse-api",
    )


# --------------------------------------------------------------------- Lever


def lever_jobs(company: str) -> list[Job]:
    """All open postings for a Lever company slug (the <slug> in jobs.lever.co/<slug>)."""
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
                backend="lever-api",
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
                backend="ashby-api",
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
    limit: int = 100,
    remote_only: bool = False,
    errors: list[str] | None = None,
    failures: list[JobsError] | None = None,
) -> list[Job]:
    """LinkedIn's unauthenticated job search (the same endpoint the public /jobs page uses).

    Returns title / company / location / url / posted date only — fetch the page for the
    description. Be gentle: this is HTML scraping of a public page, rate-limited by LinkedIn.

    Pages advance by the number of cards actually returned (LinkedIn serves 10 per page; a
    fixed step skips postings). A throttled page is retried with backoff; if it still fails, the
    failure goes to `errors` (message) / `failures` (JobsError) when given; otherwise it raises
    a JobsError (RATE_LIMITED for 429/999, UPSTREAM_BROKEN for 5xx) unless some jobs were collected.
    """
    jobs: list[Job] = []
    seen: set[str] = set()
    start = 0
    with _client() as c:
        while len(jobs) < limit and start < LI_MAX_START:
            params = {
                "keywords": keywords,
                "location": location,
                "f_TPR": f"r{hours * 3600}",
                "start": start,
            }
            if remote_only:
                params["f_WT"] = "2"
            url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
            if start:
                time.sleep(LI_PAGE_DELAY)
            r = _li_get(c, url, params)
            if r.status_code != 200:
                msg = (
                    f"linkedin {keywords!r} @ {location!r}: "
                    f"HTTP {r.status_code} at start={start}, kept {len(jobs)}"
                )
                err = JobsError(http_status_code(r.status_code), msg, source="linkedin-guest")
                if errors is not None or failures is not None:
                    if errors is not None:
                        errors.append(msg)
                    if failures is not None:
                        failures.append(err)
                    break
                if not jobs:
                    raise err
                break
            if not r.text.strip():
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
                url_ = html.unescape(m_url.group(1)).split("?")[0] if m_url else ""
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
                        url=url_,
                        posted_at=m_time.group(1) if m_time else None,
                        description=None,
                        backend="linkedin-guest",
                    )
                )
                if len(jobs) >= limit:
                    break
            start += len(cards)
    return jobs


def _li_get(c: httpx.Client, url: str, params: dict[str, Any] | None = None) -> httpx.Response:
    """GET a LinkedIn guest URL, retrying throttled (429 / 999) and 5xx answers with backoff."""
    r = c.get(url, params=params)
    for delay in LI_RETRY_DELAYS:
        if r.status_code not in (429, 999) and r.status_code < 500:
            break
        time.sleep(delay)
        r = c.get(url, params=params)
    return r


_LI_JOB_ID = re.compile(r"(?:/jobs/view/(?:[^/?#]*-)?|currentJobId=|jobPosting[:/])(\d{6,})")
_LI_D_TITLE = re.compile(r'<h[12] class="top-card-layout__title[^"]*">\s*(.*?)\s*</h[12]>', re.S)
_LI_D_COMPANY = re.compile(r'class="topcard__org-name-link[^"]*"[^>]*>\s*(.*?)\s*</a>', re.S)
_LI_D_LOC = re.compile(r'<span class="topcard__flavor topcard__flavor--bullet">\s*(.*?)\s*</span>', re.S)
_LI_D_POSTED = re.compile(r'<span class="posted-time-ago__text[^"]*">\s*(.*?)\s*</span>', re.S)
_LI_D_DESC = re.compile(
    r'<div class="show-more-less-html__markup[^"]*">(.*?)</div>\s*(?:<button|</section>)', re.S
)
_LI_D_CRITERIA = re.compile(
    r'<h3 class="description__job-criteria-subheader">\s*(.*?)\s*</h3>\s*'
    r'<span class="description__job-criteria-text[^"]*">\s*(.*?)\s*</span>',
    re.S,
)


def linkedin_job_id(target: str) -> str:
    """'4012345678', '.../jobs/view/backend-engineer-at-acme-4012345678?x', '...?currentJobId=401…'
    → '4012345678'."""
    t = str(target).strip()
    if re.fullmatch(r"\d{6,}", t):
        return t
    m = _LI_JOB_ID.search(t)
    if not m:
        raise JobsError(
            BAD_INPUT,
            f"not a LinkedIn job id or job URL: {t[:120]!r}",
            "Pass the numeric posting id or a linkedin.com/jobs/view/... URL.",
        )
    return m.group(1)


def linkedin_guest_job(target: str) -> Job:
    """One LinkedIn posting with its description, from the public (logged-out) job page.

    `target` is the numeric id or any LinkedIn job URL. The seniority / employment type /
    function / industry box and the relative "posted" text lead the description, since the
    page has no absolute date."""
    job_id = linkedin_job_id(target)
    url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
    with _client() as c:
        r = _li_get(c, url)
    if r.status_code != 200:
        code = http_status_code(r.status_code)
        msg = f"linkedin job {job_id}: HTTP {r.status_code}"
        hint = "The posting is gone or the id is wrong; do not retry it." if code == NOT_FOUND else None
        raise JobsError(code, msg, hint, source="linkedin-guest")
    page = r.text
    title = _strip_html(_group(_LI_D_TITLE, page))
    if not title:
        if "authwall" in str(r.url) or "authwall" in page[:5000]:
            raise JobsError(
                NEED_LOGIN, f"linkedin job {job_id}: LinkedIn asked for a login", source="linkedin-guest"
            )
        raise JobsError(
            UPSTREAM_BROKEN,
            f"linkedin job {job_id}: page has no job title (layout changed?)",
            "LinkedIn's public page did not look like a job posting; open the url instead and tell the "
            "user the parser may need updating.",
            source="linkedin-guest",
        )
    header = [f"{_strip_html(k)}: {_strip_html(v)}" for k, v in _LI_D_CRITERIA.findall(page)]
    posted = _strip_html(_group(_LI_D_POSTED, page))
    if posted:
        header.insert(0, f"Posted: {posted}")
    desc = _strip_html(_group(_LI_D_DESC, page))
    if header:
        desc = "\n".join(header) + ("\n\n" + desc if desc else "")
    return Job(
        source="linkedin",
        board="guest",
        id=job_id,
        title=title,
        company=_strip_html(_group(_LI_D_COMPANY, page)) or "",
        location=_strip_html(_group(_LI_D_LOC, page)) or "",
        remote=None,
        url=f"https://www.linkedin.com/jobs/view/{job_id}",
        posted_at=None,
        description=desc or None,
        backend="linkedin-guest",
    )


def _group(rx: re.Pattern[str], s: str) -> str | None:
    m = rx.search(s)
    return m.group(1) if m else None


# -------------------------------------------------------------------- helpers


def newer_than(job: Job, hours: int) -> bool:
    """True when the job has a timestamp within `hours`, or no timestamp at all (unknown → keep)."""
    ts = job.get("posted_at")
    if not ts:
        return True
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", ts):
        # A bare date (LinkedIn) is a local calendar day: its last instant can be as late as
        # the next day 12:00 UTC (UTC-12). Keep it if any part of that day is inside the window.
        try:
            day = datetime.fromisoformat(ts).replace(tzinfo=timezone.utc)
        except ValueError:
            return True
        return day + timedelta(days=1, hours=12) >= cutoff
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return True
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt >= cutoff


def parse_board(spec: str) -> tuple[str, str]:
    """'greenhouse:doordashcanada' -> ('greenhouse', 'doordashcanada')."""
    if ":" not in spec:
        raise ValueError(f"board spec must be 'source:slug', got {spec!r}")
    source, slug = spec.split(":", 1)
    source = source.strip().lower()
    if source not in {"greenhouse", "lever", "ashby"}:
        raise ValueError(f"unknown source {source!r}; use greenhouse, lever or ashby")
    return source, slug.strip()


def fetch_board(spec: str, with_content: bool = False) -> list[Job]:
    """All jobs on one board. Lever and Ashby always include descriptions; Greenhouse only with
    `with_content` (one heavier request instead of one per job)."""
    source, slug = parse_board(spec)
    if source == "greenhouse":
        return greenhouse_jobs(slug, with_content=with_content)
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
