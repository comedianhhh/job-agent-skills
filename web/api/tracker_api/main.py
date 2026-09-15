"""tracker-api — HTTP surface over career/tracker.md + jobs-mcp scans.

CAREER_DIR=/path/to/career uvicorn --factory tracker_api.main:create_app --reload
"""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import Settings, load_settings
from .db import TRIAGE, Event, Posting, Scan, make_session_factory
from .scans import load_targets, run_scan, scan_params
from .tracker import STATUSES, Row, Tracker, TrackerError, business_days_between

FOLLOW_UP_BUSINESS_DAYS = 10
GHOST_AFTER_DAYS = 24  # ~10 business days + 2 weeks, per the /offer rule


router = APIRouter(prefix="/api")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    app = FastAPI(title="tracker-api", version="0.1.0")
    app.add_middleware(
        CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
    )  # local tool, no auth
    app.state.settings = settings
    app.state.sessions = make_session_factory(settings.database_url)
    app.include_router(router)
    return app


# ------------------------------------------------------------------ helpers


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_db(request: Request):
    db: Session = request.app.state.sessions()
    try:
        yield db
    finally:
        db.close()


def get_tracker(request: Request) -> Tracker:
    return Tracker(request.app.state.settings.tracker_path)


class RowOut(BaseModel):
    id: str
    company: str
    role: str
    req: str
    location: str
    applied: str
    applied_on: date | None
    status: str | None
    status_raw: str
    next_step: str
    folder_text: str
    folder_href: str
    days_since_applied: int | None = None
    follow_up_due: bool = False
    ghost_candidate: bool = False

    @classmethod
    def from_row(cls, r: Row, today: date | None = None) -> RowOut:
        today = today or date.today()
        out = cls(
            id=r.id,
            company=r.company,
            role=r.role,
            req=r.req,
            location=r.location,
            applied=r.applied,
            applied_on=r.applied_on,
            status=r.status,
            status_raw=r.status_raw,
            next_step=r.next_step,
            folder_text=r.folder_text,
            folder_href=r.folder_href,
        )
        if r.applied_on:
            out.days_since_applied = (today - r.applied_on).days
            if r.status == "APPLIED":
                bd = business_days_between(r.applied_on, today)
                out.follow_up_due = bd >= FOLLOW_UP_BUSINESS_DAYS
                out.ghost_candidate = out.days_since_applied >= GHOST_AFTER_DAYS
        return out


class RowPatch(BaseModel):
    status: str | None = None
    next_step: str | None = None
    applied: str | None = None
    location: str | None = None
    req: str | None = None
    note: str = ""


class RowCreate(BaseModel):
    company: str = Field(min_length=1)
    role: str = Field(min_length=1)
    req: str = ""
    location: str = ""
    applied: str = "—"
    status: str = "DRAFT"
    next_step: str = ""
    folder: str = ""


class EventOut(BaseModel):
    id: int
    row_id: str
    from_status: str | None
    to_status: str
    note: str
    at: str


class ScanRequest(BaseModel):
    hours: int | None = None
    boards: list[str] | None = None
    linkedin: list[dict[str, Any]] | None = None
    include_regex: str | None = None
    exclude_regex: str | None = None
    location_regex: str | None = None
    limit: int | None = None
    write_scan_file: bool = True


class ScanOut(BaseModel):
    id: int
    started_at: str
    finished_at: str | None
    params: dict[str, Any]
    scanned: int
    matched: int
    new: int
    errors: list[str]


class PostingOut(BaseModel):
    id: int
    source: str
    board: str
    external_id: str
    title: str
    company: str
    location: str
    url: str
    posted_at: str | None
    first_seen: str
    last_seen: str
    times_seen: int
    triage: str
    note: str
    tracker_row_id: str | None
    scan_id: int | None


class PostingPatch(BaseModel):
    triage: Literal["new", "shortlisted", "dismissed", "tracked"] | None = None
    note: str | None = None


def _event_out(e: Event) -> EventOut:
    return EventOut(
        id=e.id,
        row_id=e.row_id,
        from_status=e.from_status,
        to_status=e.to_status,
        note=e.note,
        at=e.at.isoformat(),
    )


def _scan_out(s: Scan) -> ScanOut:
    return ScanOut(
        id=s.id,
        started_at=s.started_at.isoformat(),
        finished_at=s.finished_at.isoformat() if s.finished_at else None,
        params=s.params,
        scanned=s.scanned,
        matched=s.matched,
        new=s.new,
        errors=list(s.errors or []),
    )


def _posting_out(p: Posting) -> PostingOut:
    return PostingOut(
        id=p.id,
        source=p.source,
        board=p.board,
        external_id=p.external_id,
        title=p.title,
        company=p.company,
        location=p.location,
        url=p.url,
        posted_at=p.posted_at,
        first_seen=p.first_seen.isoformat(),
        last_seen=p.last_seen.isoformat(),
        times_seen=p.times_seen,
        triage=p.triage,
        note=p.note,
        tracker_row_id=p.tracker_row_id,
        scan_id=p.scan_id,
    )


# ------------------------------------------------------------------- routes


@router.get("/health")
def health(settings: Settings = Depends(get_settings)):
    return {
        "ok": True,
        "career_dir": str(settings.career_dir),
        "tracker_exists": settings.tracker_path.exists(),
        "database": settings.database_url.split("@")[-1],  # never echo credentials
    }


@router.get("/tracker")
def list_rows(tracker: Tracker = Depends(get_tracker)):
    if not tracker.path.exists():
        raise HTTPException(404, f"{tracker.path} not found — run /career-init or set CAREER_DIR")
    try:
        rows = tracker.rows()
    except TrackerError as e:
        raise HTTPException(422, str(e)) from e
    out = [RowOut.from_row(r) for r in rows]
    return {"statuses": STATUSES, "rows": out, "path": str(tracker.path)}


@router.post("/tracker", status_code=201)
def create_row(body: RowCreate, tracker: Tracker = Depends(get_tracker), db: Session = Depends(get_db)):
    try:
        row = tracker.add(**body.model_dump())
    except TrackerError as e:
        raise HTTPException(422, str(e)) from e
    db.add(
        Event(row_id=row.id, company=row.company, role=row.role, from_status=None, to_status=row.status or "")
    )
    db.commit()
    return RowOut.from_row(row)


@router.patch("/tracker/{row_id}")
def patch_row(
    row_id: str, body: RowPatch, tracker: Tracker = Depends(get_tracker), db: Session = Depends(get_db)
):
    try:
        before = tracker.get(row_id)
    except KeyError as e:
        raise HTTPException(404, "row not found") from e
    fields = body.model_dump(exclude={"note"}, exclude_none=True)
    if not fields:
        return RowOut.from_row(before)
    try:
        after = tracker.update(row_id, **fields)
    except TrackerError as e:
        raise HTTPException(422, str(e)) from e
    if body.status is not None and after.status != before.status:
        db.add(
            Event(
                row_id=row_id,
                company=after.company,
                role=after.role,
                from_status=before.status,
                to_status=after.status or "",
                note=body.note,
            )
        )
        db.commit()
    return RowOut.from_row(after)


@router.get("/tracker/{row_id}/events")
def row_events(row_id: str, db: Session = Depends(get_db)):
    q = select(Event).where(Event.row_id == row_id).order_by(Event.at.desc())
    return [_event_out(e) for e in db.scalars(q)]


@router.get("/events")
def recent_events(limit: int = Query(50, le=500), db: Session = Depends(get_db)):
    q = select(Event).order_by(Event.at.desc()).limit(limit)
    return [_event_out(e) for e in db.scalars(q)]


@router.get("/targets")
def targets(settings: Settings = Depends(get_settings)):
    t = load_targets(settings.targets_path)
    return {**t, "path": str(settings.targets_path), "effective": scan_params(t)}


@router.post("/scans", status_code=201)
async def start_scan(
    body: ScanRequest,
    settings: Settings = Depends(get_settings),
    tracker: Tracker = Depends(get_tracker),
    db: Session = Depends(get_db),
):
    t = load_targets(settings.targets_path)
    params = scan_params(t, body.model_dump(exclude={"write_scan_file"}, exclude_none=True))
    if not params["boards_"] and not params["linkedin_queries"]:
        raise HTTPException(422, "nothing to scan: add boards or linkedin queries to targets.yaml")
    scan = await run_in_threadpool(
        run_scan, db, tracker, settings.career_dir, params, write_scan_file=body.write_scan_file
    )
    return _scan_out(scan)


@router.get("/scans")
def list_scans(limit: int = Query(20, le=200), db: Session = Depends(get_db)):
    q = select(Scan).order_by(Scan.id.desc()).limit(limit)
    return [_scan_out(s) for s in db.scalars(q)]


@router.get("/postings")
def list_postings(
    triage: str | None = Query(None),
    scan_id: int | None = Query(None),
    limit: int = Query(200, le=1000),
    db: Session = Depends(get_db),
):
    q = select(Posting)
    if triage:
        if triage not in TRIAGE:
            raise HTTPException(422, f"triage must be one of {TRIAGE}")
        q = q.where(Posting.triage == triage)
    if scan_id is not None:
        q = q.where(Posting.scan_id == scan_id)
    q = q.order_by(Posting.first_seen.desc(), Posting.id.desc()).limit(limit)
    return [_posting_out(p) for p in db.scalars(q)]


@router.patch("/postings/{posting_id}")
def patch_posting(posting_id: int, body: PostingPatch, db: Session = Depends(get_db)):
    p = db.get(Posting, posting_id)
    if not p:
        raise HTTPException(404, "posting not found")
    if body.triage is not None:
        p.triage = body.triage
    if body.note is not None:
        p.note = body.note
    db.commit()
    return _posting_out(p)


@router.post("/postings/{posting_id}/track", status_code=201)
def track_posting(posting_id: int, tracker: Tracker = Depends(get_tracker), db: Session = Depends(get_db)):
    """Turn a scanned posting into a DRAFT tracker row (the skills then build the folder)."""
    p = db.get(Posting, posting_id)
    if not p:
        raise HTTPException(404, "posting not found")
    if p.tracker_row_id:
        raise HTTPException(409, f"already tracked as row {p.tracker_row_id}")
    req = p.external_id if p.source != "linkedin" else f"LinkedIn {p.external_id}"
    if p.source in ("greenhouse", "lever", "ashby") and p.board:
        req = f"{p.source.capitalize()} {p.board}/{p.external_id}"
    try:
        row = tracker.add(
            company=p.company,
            role=p.title,
            req=req,
            location=p.location,
            next_step=f"run /job-match — {p.url}",
        )
    except TrackerError as e:
        raise HTTPException(422, str(e)) from e
    p.triage = "tracked"
    p.tracker_row_id = row.id
    db.add(Event(row_id=row.id, company=row.company, role=row.role, from_status=None, to_status="DRAFT"))
    db.commit()
    return RowOut.from_row(row)
