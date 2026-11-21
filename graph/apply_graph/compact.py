"""Compact closed applications: a REJECTED / GHOSTED role folder becomes one line in archive.md plus the
files nothing else can rebuild. Code only; the graph asks the human before `apply` deletes anything.

Rule: keep what cannot be regenerated and is still used; delete what can be rebuilt or lives elsewhere.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from pydantic import BaseModel

CLOSED = {"REJECTED", "GHOSTED"}
ARCHIVE_DIR = "_archive"

KEEP = {"03-Job-Description.md", "01-Resume.html"}
DERIVED = {"02-Cover-Letter.md", "05-Form-Answers.md"}
PREP = re.compile(r"interview-prep|cheat-sheet|^00-prep\.html$|\.graph\.md$|\.sqlite$", re.I)


class FilePlan(BaseModel):
    name: str
    action: str  # keep | delete | unknown
    why: str


class Candidate(BaseModel):
    folder: str
    company: str
    role: str
    status: str
    date: str
    interviewed: bool  # had interview prep -> ask for a lesson
    files: list[FilePlan]


class Approval(BaseModel):
    folder: str
    lesson: str = ""
    delete_unknown: list[str] = []


def classify(name: str, names: set[str]) -> FilePlan:
    if name in KEEP:
        return FilePlan(name=name, action="keep", why="cannot be rebuilt; eval uses it")
    if name in DERIVED or "cover-letter" in name.lower():
        return FilePlan(name=name, action="delete", why="derived from facts.md / answers.yaml")
    if PREP.search(name):
        return FilePlan(name=name, action="delete", why="working notes (lesson goes on the archive line)")
    if name.lower().endswith(".pdf"):
        if "01-Resume.html" in names:
            return FilePlan(
                name=name, action="delete", why="render-resume.sh rebuilds it from 01-Resume.html"
            )
        return FilePlan(name=name, action="keep", why="only record of what was sent")
    return FilePlan(name=name, action="unknown", why="unknown file: kept unless ticked")


def tracker_rows(text: str) -> list[tuple[int, dict[str, str]]]:
    """(line index, {column: cell}) for every row of every table that has Status and Folder columns."""
    rows, header = [], None
    for i, line in enumerate(text.splitlines()):
        if not line.startswith("|"):
            header = None
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if header is None:
            header = cells
            continue
        if all(re.fullmatch(r":?-+:?", c) for c in cells):  # the |---|---| separator
            continue
        if "Status" in header and "Folder" in header and len(cells) == len(header):
            rows.append((i, dict(zip(header, cells, strict=True))))
    return rows


def candidates(career: Path) -> list[Candidate]:
    tracker = career / "tracker.md"
    if not tracker.is_file():
        return []
    out = []
    for _, row in tracker_rows(tracker.read_text(encoding="utf-8")):
        folder = row["Folder"]
        if row["Status"] not in CLOSED or not folder or folder.startswith(ARCHIVE_DIR):
            continue
        d = career / folder
        if d.parent != career or not d.is_dir():
            continue
        names = {p.name for p in d.iterdir() if p.is_file()}
        files = [classify(n, names) for n in sorted(names)]
        files += [
            FilePlan(name=p.name + "/", action="unknown", why="sub-folder") for p in d.iterdir() if p.is_dir()
        ]
        applied = row.get("Applied", "")
        date = applied if re.match(r"\d{4}-\d{2}-\d{2}", applied) else folder[:10]
        out.append(
            Candidate(
                folder=folder,
                company=row.get("Company", ""),
                role=row.get("Role", ""),
                status=row["Status"],
                date=date,
                interviewed=any(PREP.search(n) for n in names),
                files=files,
            )
        )
    return out


def archive_line(c: Candidate, lesson: str) -> str:
    line = f"- {c.date} | {c.company} | {c.role} | {c.status}"
    lesson = " ".join(lesson.split())
    return line + (f" | lesson: {lesson}" if lesson and lesson.lower() != "none" else "")


def apply(career: Path, approvals: list[Approval]) -> list[str]:
    """Move keep files to _archive/<folder>/, delete the rest, add archive lines, repoint tracker rows."""
    by_folder = {c.folder: c for c in candidates(career)}
    tracker = career / "tracker.md"
    lines = tracker.read_text(encoding="utf-8").splitlines(keepends=True)
    row_at = {row["Folder"]: i for i, row in tracker_rows("".join(lines))}
    written = []
    for a in approvals:
        c = by_folder.get(a.folder)
        if c is None:  # not closed, already archived, or not in the tracker: never touch it
            continue
        src, dest = career / c.folder, career / ARCHIVE_DIR / c.folder
        dest.mkdir(parents=True, exist_ok=True)
        for f in c.files:
            keep = f.action == "keep" or (f.action == "unknown" and f.name not in a.delete_unknown)
            if keep:
                shutil.move(str(src / f.name.rstrip("/")), dest / f.name.rstrip("/"))
        shutil.rmtree(src)
        line = archive_line(c, a.lesson)
        with (career / "archive.md").open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
        i = row_at[c.folder]
        lines[i] = lines[i].replace(f"| {c.folder} |", f"| {ARCHIVE_DIR}/{c.folder} |", 1)
        written.append(line)
    if written:
        tracker.write_text("".join(lines), encoding="utf-8")
    return written
