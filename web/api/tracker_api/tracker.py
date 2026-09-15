"""Read and write the pipeline table in `career/tracker.md`.

The markdown file stays the single record (the `/offer` skill and the user edit it too), so this
module never rewrites the file wholesale: it locates the 8-column table, parses rows into `Row`
objects, and on update rebuilds only the cells that changed on the one line that changed. The
prose around the table, every other row, and the line-ending style are left byte-for-byte alone.

Column order is positional (the header text may be in any language):
    Company | Role | Req | Location | Applied | Status | Next step | Folder
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

STATUSES = [
    "DRAFT",
    "BLOCKED",
    "APPLIED",
    "SCREEN",
    "OA",
    "TECH",
    "ONSITE",
    "OFFER",
    "REJECTED",
    "GHOSTED",
    "WITHDRAWN",
]
COLUMNS = 8
COL = {
    name: i
    for i, name in enumerate(
        ["company", "role", "req", "location", "applied", "status", "next_step", "folder"]
    )
}

_SEP_LINE = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$")
_LINK = re.compile(r"\[([^\]]*)\]\(([^)]*)\)")
_DATE = re.compile(r"(\d{4}-\d{2}-\d{2})")
_STATUS = re.compile(r"\b(" + "|".join(STATUSES) + r")\b")


def _split_cells(line: str) -> list[str]:
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|") and not s.endswith("\\|"):
        s = s[:-1]
    cells = re.split(r"(?<!\\)\|", s)
    return [c.strip() for c in cells]


def _join_cells(cells: list[str]) -> str:
    return "| " + " | ".join(cells) + " |"


def clean(s: str) -> str:
    """Markdown emphasis off, text only."""
    s = _LINK.sub(lambda m: m.group(1), s)
    s = s.replace("**", "").replace("`", "").replace("~~", "")
    return s.strip()


def _row_id(folder_href: str, company: str, role: str, req: str) -> str:
    key = folder_href or f"{company}|{role}|{req}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:10]


@dataclass
class Row:
    line_no: int  # 0-based index into the file's lines
    cells: list[str]  # raw markdown cells, exactly COLUMNS long
    id: str = ""
    company: str = ""
    role: str = ""
    req: str = ""
    location: str = ""
    applied: str = ""
    applied_on: date | None = None
    status: str | None = None  # one of STATUSES, or None when the cell does not name one
    status_raw: str = ""
    next_step: str = ""
    folder_text: str = ""
    folder_href: str = ""
    extra: list[str] = field(default_factory=list)  # cells beyond the 8th, preserved verbatim

    @classmethod
    def from_line(cls, line_no: int, line: str) -> Row:
        cells = _split_cells(line)
        extra = cells[COLUMNS:]
        cells = (cells + [""] * COLUMNS)[:COLUMNS]
        r = cls(line_no=line_no, cells=cells, extra=extra)
        r.company = clean(cells[COL["company"]])
        r.role = clean(cells[COL["role"]])
        r.req = clean(cells[COL["req"]])
        r.location = clean(cells[COL["location"]])
        r.applied = clean(cells[COL["applied"]])
        m = _DATE.search(r.applied)
        r.applied_on = date.fromisoformat(m.group(1)) if m else None
        r.status_raw = cells[COL["status"]]
        m = _STATUS.search(clean(r.status_raw).upper())
        r.status = m.group(1) if m else None
        r.next_step = cells[COL["next_step"]]
        folder = cells[COL["folder"]]
        m = _LINK.search(folder)
        if m:
            r.folder_text, r.folder_href = m.group(1), m.group(2)
        else:
            r.folder_text, r.folder_href = clean(folder), ""
        r.id = _row_id(r.folder_href, r.company, r.role, r.req)
        return r

    def to_line(self) -> str:
        return _join_cells(self.cells + self.extra)


@dataclass
class Table:
    header_line: int
    sep_line: int
    rows: list[Row]
    uses_backtick_status: bool

    @property
    def last_line(self) -> int:
        return self.rows[-1].line_no if self.rows else self.sep_line


class TrackerError(Exception):
    pass


class Tracker:
    def __init__(self, path: Path):
        self.path = Path(path)

    # ------------------------------------------------------------------ read

    def _read(self) -> tuple[list[str], str]:
        with self.path.open(encoding="utf-8", newline="") as f:  # newline="" keeps CRLF as-is
            text = f.read()
        nl = "\r\n" if "\r\n" in text else "\n"
        return text.split(nl), nl

    def _find_table(self, lines: list[str]) -> Table:
        i = 0
        while i < len(lines) - 1:
            if lines[i].lstrip().startswith("|") and _SEP_LINE.match(lines[i + 1]):
                if len(_split_cells(lines[i])) >= COLUMNS:
                    rows: list[Row] = []
                    j = i + 2
                    while j < len(lines) and lines[j].lstrip().startswith("|"):
                        rows.append(Row.from_line(j, lines[j]))
                        j += 1
                    ticks = sum(1 for r in rows if "`" in r.status_raw)
                    return Table(i, i + 1, rows, uses_backtick_status=ticks >= max(1, len(rows) // 2))
                i += 2
                continue
            i += 1
        raise TrackerError(f"no {COLUMNS}-column pipeline table found in {self.path}")

    def rows(self) -> list[Row]:
        lines, _ = self._read()
        return self._find_table(lines).rows

    def get(self, row_id: str) -> Row:
        for r in self.rows():
            if r.id == row_id:
                return r
        raise KeyError(row_id)

    # ----------------------------------------------------------------- write

    def update(
        self,
        row_id: str,
        *,
        status: str | None = None,
        next_step: str | None = None,
        applied: str | None = None,
        location: str | None = None,
        req: str | None = None,
    ) -> Row:
        lines, nl = self._read()
        table = self._find_table(lines)
        row = next((r for r in table.rows if r.id == row_id), None)
        if row is None:
            raise KeyError(row_id)
        if status is not None:
            status = status.strip().upper()
            if status not in STATUSES:
                raise TrackerError(f"unknown status {status!r}; expected one of {STATUSES}")
            ticks = "`" in row.status_raw or (not row.status_raw and table.uses_backtick_status)
            row.cells[COL["status"]] = f"`{status}`" if ticks else status
        if next_step is not None:
            row.cells[COL["next_step"]] = _escape(next_step)
        if applied is not None:
            row.cells[COL["applied"]] = _escape(applied)
        if location is not None:
            row.cells[COL["location"]] = _escape(location)
        if req is not None:
            row.cells[COL["req"]] = _escape(req)
        lines[row.line_no] = row.to_line()
        self.path.write_text(nl.join(lines), encoding="utf-8", newline="")
        return Row.from_line(row.line_no, lines[row.line_no])

    def add(
        self,
        *,
        company: str,
        role: str,
        req: str = "",
        location: str = "",
        applied: str = "—",
        status: str = "DRAFT",
        next_step: str = "",
        folder: str = "",
    ) -> Row:
        status = status.strip().upper()
        if status not in STATUSES:
            raise TrackerError(f"unknown status {status!r}")
        lines, nl = self._read()
        table = self._find_table(lines)
        folder_cell = f"[{folder.rstrip('/')}]({folder.rstrip('/')}/)" if folder else ""
        cells = [
            _escape(company),
            _escape(role),
            _escape(req) or "—",
            _escape(location),
            _escape(applied) or "—",
            f"`{status}`" if table.uses_backtick_status else status,
            _escape(next_step),
            folder_cell,
        ]
        line = _join_cells(cells)
        new_row = Row.from_line(table.last_line + 1, line)
        if any(r.id == new_row.id for r in table.rows):
            raise TrackerError("a row for this application already exists")
        lines.insert(table.last_line + 1, line)
        self.path.write_text(nl.join(lines), encoding="utf-8", newline="")
        return new_row


def _escape(s: str) -> str:
    """Cells cannot contain a bare pipe or a newline."""
    return s.replace("\r", " ").replace("\n", " ").replace("|", "\\|").strip()


def business_days_between(start: date, end: date) -> int:
    """Weekdays strictly after `start` up to and including `end`."""
    if end <= start:
        return 0
    days = 0
    d = start
    while d < end:
        d = date.fromordinal(d.toordinal() + 1)
        if d.weekday() < 5:
            days += 1
    return days
