"""Machine state that does not belong in tracker.md: status-change events, scan runs, scanned postings.

Postgres in docker-compose; SQLite for local development and tests (DATABASE_URL decides).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)  # naive UTC works the same on sqlite + pg


class Base(DeclarativeBase):
    pass


class Event(Base):
    """One status transition on a tracker row (the row itself lives in tracker.md)."""

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    row_id: Mapped[str] = mapped_column(String(16), index=True)
    company: Mapped[str] = mapped_column(String(200), default="")
    role: Mapped[str] = mapped_column(String(300), default="")
    from_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    to_status: Mapped[str] = mapped_column(String(16))
    note: Mapped[str] = mapped_column(Text, default="")
    at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class Scan(Base):
    __tablename__ = "scans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    params: Mapped[dict] = mapped_column(JSON, default=dict)
    scanned: Mapped[int] = mapped_column(Integer, default=0)  # raw postings fetched
    matched: Mapped[int] = mapped_column(Integer, default=0)  # after jobs-mcp filters
    new: Mapped[int] = mapped_column(Integer, default=0)  # never seen before
    errors: Mapped[list] = mapped_column(JSON, default=list)

    postings: Mapped[list[Posting]] = relationship(back_populates="scan")


TRIAGE = ("new", "shortlisted", "dismissed", "tracked")


class Posting(Base):
    """A job posting seen by a scan, keyed by URL so re-scans update instead of duplicate."""

    __tablename__ = "postings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(600), unique=True, index=True)
    source: Mapped[str] = mapped_column(String(20))
    board: Mapped[str] = mapped_column(String(100), default="")
    external_id: Mapped[str] = mapped_column(String(100), default="")
    title: Mapped[str] = mapped_column(String(300), default="")
    company: Mapped[str] = mapped_column(String(200), default="")
    location: Mapped[str] = mapped_column(String(200), default="")
    url: Mapped[str] = mapped_column(String(600), default="")
    posted_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    first_seen: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    times_seen: Mapped[int] = mapped_column(Integer, default=1)
    triage: Mapped[str] = mapped_column(String(16), default="new", index=True)
    note: Mapped[str] = mapped_column(Text, default="")
    tracker_row_id: Mapped[str | None] = mapped_column(String(16), nullable=True)
    scan_id: Mapped[int | None] = mapped_column(ForeignKey("scans.id"), nullable=True)

    scan: Mapped[Scan | None] = relationship(back_populates="postings")


def make_engine(url: str):
    kw = (
        {"connect_args": {"check_same_thread": False}}
        if url.startswith("sqlite")
        else {"pool_pre_ping": True}
    )
    return create_engine(url, **kw)


def make_session_factory(url: str) -> sessionmaker[Session]:
    engine = make_engine(url)
    Base.metadata.create_all(engine)
    return sessionmaker(engine, expire_on_commit=False)
