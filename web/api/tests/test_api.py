"""HTTP surface: tracker rows, events, scans (jobs-mcp stubbed), postings triage."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest

from tracker_api import scans
from tracker_api.main import RowOut
from tracker_api.tracker import Row


def test_health(client, career: Path):
    r = client.get("/api/health").json()
    assert r["ok"] and r["tracker_exists"]
    assert r["career_dir"] == str(career)


def test_list_rows(client):
    r = client.get("/api/tracker")
    assert r.status_code == 200
    body = r.json()
    assert body["statuses"][0] == "DRAFT"
    assert [x["company"] for x in body["rows"]] == ["Affirm", "Cohere", "Clio", "Emterra", "Mystery"]
    assert body["rows"][0]["applied_on"] == "2026-09-12"
    assert body["rows"][4]["status"] is None


def test_list_rows_missing_tracker(client, career: Path):
    (career / "tracker.md").unlink()
    assert client.get("/api/tracker").status_code == 404


def test_patch_status_records_event(client):
    rows = client.get("/api/tracker").json()["rows"]
    cohere = rows[1]
    r = client.patch(
        f"/api/tracker/{cohere['id']}", json={"status": "SCREEN", "note": "recruiter email 9/16"}
    )
    assert r.status_code == 200
    assert r.json()["status"] == "SCREEN"
    ev = client.get(f"/api/tracker/{cohere['id']}/events").json()
    assert len(ev) == 1
    assert ev[0]["from_status"] == "APPLIED" and ev[0]["to_status"] == "SCREEN"
    assert ev[0]["note"] == "recruiter email 9/16"
    # same status again → no new event
    client.patch(f"/api/tracker/{cohere['id']}", json={"status": "SCREEN"})
    assert len(client.get(f"/api/tracker/{cohere['id']}/events").json()) == 1
    assert len(client.get("/api/events").json()) == 1


def test_patch_next_step_only(client):
    row = client.get("/api/tracker").json()["rows"][2]
    r = client.patch(f"/api/tracker/{row['id']}", json={"next_step": "applied via Workday 9/16"})
    assert r.json()["next_step"] == "applied via Workday 9/16"
    assert r.json()["status"] == "DRAFT"
    assert client.get(f"/api/tracker/{row['id']}/events").json() == []


def test_patch_validation(client):
    row = client.get("/api/tracker").json()["rows"][0]
    assert client.patch(f"/api/tracker/{row['id']}", json={"status": "HIRED"}).status_code == 422
    assert client.patch("/api/tracker/zzz", json={"status": "APPLIED"}).status_code == 404
    assert client.patch(f"/api/tracker/{row['id']}", json={}).json()["id"] == row["id"]


def test_create_row(client):
    r = client.post(
        "/api/tracker",
        json={"company": "Shopify", "role": "Developer", "req": "Lever 1", "location": "Remote"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "DRAFT"
    rows = client.get("/api/tracker").json()["rows"]
    assert rows[-1]["id"] == body["id"]
    assert client.get(f"/api/tracker/{body['id']}/events").json()[0]["to_status"] == "DRAFT"
    assert (
        client.post(
            "/api/tracker", json={"company": "Shopify", "role": "Developer", "req": "Lever 1"}
        ).status_code
        == 422
    )
    assert client.post("/api/tracker", json={"company": "", "role": "x"}).status_code == 422


def test_follow_up_flags():
    today = date(2026, 9, 28)  # Monday
    base = "| A | B | 1 | L | {applied} | APPLIED | n | [f](f/) |"
    r = Row.from_line(0, base.format(applied="2026-09-12"))  # 11 business days earlier
    out = RowOut.from_row(r, today)
    assert out.follow_up_due and not out.ghost_candidate
    assert out.days_since_applied == 16
    r = Row.from_line(0, base.format(applied="2026-09-22"))
    assert not RowOut.from_row(r, today).follow_up_due
    r = Row.from_line(0, base.format(applied=(today - timedelta(days=30)).isoformat()))
    assert RowOut.from_row(r, today).ghost_candidate
    r = Row.from_line(0, base.format(applied="2026-09-01").replace("APPLIED", "SCREEN"))
    assert not RowOut.from_row(r, today).follow_up_due  # only APPLIED rows need chasing


# -------------------------------------------------------------------- scans


def test_targets(client, career: Path):
    t = client.get("/api/targets").json()
    assert t["boards"] == ["greenhouse:doordashcanada", "ashby:cohere"]
    eff = t["effective"]
    assert eff["hours"] == 48
    assert eff["exclude_regex"] is None  # "" in yaml means no exclusion
    assert eff["location_regex"] == "Toronto|Canada|Remote"


FAKE_JOBS = [
    {
        "source": "greenhouse",
        "board": "doordashcanada",
        "id": "7981805003",  # matches the Affirm row's req → tracked
        "title": "Software Engineer II",
        "company": "affirm",
        "location": "Remote Canada",
        "url": "https://boards.greenhouse.io/affirm/jobs/7981805003",
        "posted_at": "2026-09-15T10:00:00Z",
        "description": "",
    },
    {
        "source": "ashby",
        "board": "cohere",
        "id": "abc",
        "title": "Backend Engineer",
        "company": "cohere",
        "location": "Toronto",
        "url": "https://jobs.ashbyhq.com/cohere/abc",
        "posted_at": "2026-09-15",
        "description": "",
    },
    {
        "source": "linkedin",
        "board": "guest",
        "id": "4458535812",
        "title": "Application Developer",
        "company": "RBC",
        "location": "Toronto, Ontario, Canada",
        "url": "https://ca.linkedin.com/jobs/view/application-developer-4458535812",
        "posted_at": "2026-09-15",
        "description": None,
    },
]


@pytest.fixture
def fake_scan(monkeypatch):
    calls: list[dict] = []

    def scan(**kw):
        calls.append(kw)
        return {"count": len(FAKE_JOBS), "scanned": 10, "jobs": list(FAKE_JOBS), "errors": ["lever:x: 404"]}

    monkeypatch.setattr(scans.jobs, "scan", scan)
    return calls


def test_scan_persists_and_writes_scan_file(client, career: Path, fake_scan):
    r = client.post("/api/scans", json={"hours": 6})
    assert r.status_code == 201, r.text
    s = r.json()
    assert s["scanned"] == 10 and s["matched"] == 3 and s["new"] == 3
    assert s["errors"] == ["lever:x: 404"]
    assert fake_scan[0]["hours"] == 6
    assert fake_scan[0]["boards_"] == ["greenhouse:doordashcanada", "ashby:cohere"]
    assert fake_scan[0]["linkedin_queries"][0]["keywords"] == "backend engineer"

    posts = client.get("/api/postings").json()
    assert len(posts) == 3
    by_id = {p["external_id"]: p for p in posts}
    assert by_id["7981805003"]["triage"] == "tracked"
    assert by_id["7981805003"]["tracker_row_id"] == client.get("/api/tracker").json()["rows"][0]["id"]
    assert by_id["abc"]["triage"] == "new"

    scan_files = list(career.glob("SCAN-*.md"))
    assert len(scan_files) == 1
    text = scan_files[0].read_text(encoding="utf-8")
    assert text.startswith("# Scan — ")
    assert "| Company | Role | Location | Posted | URL | first-look GAP |" in text
    assert "jobs.ashbyhq.com/cohere/abc" in text
    assert "linkedin.com/jobs/view/application-developer" in text
    assert "greenhouse.io/affirm" not in text  # already tracked → not re-listed

    # second scan: same jobs → nothing new, times_seen bumps, scan file unchanged
    s2 = client.post("/api/scans", json={}).json()
    assert s2["new"] == 0 and s2["matched"] == 3
    assert client.get("/api/postings?triage=new").json()[0]["times_seen"] == 2
    assert scan_files[0].read_text(encoding="utf-8") == text
    assert [x["id"] for x in client.get("/api/scans").json()] == [s2["id"], s["id"]]


def test_scan_requires_targets(client, career: Path, fake_scan):
    (career / "targets.yaml").write_text("boards: []\n", encoding="utf-8")
    assert client.post("/api/scans", json={}).status_code == 422
    assert client.post("/api/scans", json={"boards": ["lever:paytm"]}).status_code == 201
    assert fake_scan[0]["boards_"] == ["lever:paytm"]


def test_posting_triage_and_track(client, career: Path, fake_scan):
    client.post("/api/scans", json={"write_scan_file": False})
    assert not list(career.glob("SCAN-*.md"))
    new = client.get("/api/postings?triage=new").json()
    cohere = next(p for p in new if p["external_id"] == "abc")

    r = client.patch(f"/api/postings/{cohere['id']}", json={"triage": "shortlisted", "note": "CA$ band ok"})
    assert r.json()["triage"] == "shortlisted" and r.json()["note"] == "CA$ band ok"
    assert client.patch(f"/api/postings/{cohere['id']}", json={"triage": "bogus"}).status_code == 422
    assert client.get("/api/postings?triage=bogus").status_code == 422

    r = client.post(f"/api/postings/{cohere['id']}/track")
    assert r.status_code == 201, r.text
    row = r.json()
    assert row["company"] == "cohere" and row["role"] == "Backend Engineer"
    assert row["req"] == "Ashby cohere/abc"
    assert row["status"] == "DRAFT"
    assert "jobs.ashbyhq.com/cohere/abc" in row["next_step"]
    assert client.get("/api/tracker").json()["rows"][-1]["id"] == row["id"]
    p = client.get(f"/api/postings?scan_id={cohere['scan_id']}").json()
    assert next(x for x in p if x["id"] == cohere["id"])["tracker_row_id"] == row["id"]
    assert client.post(f"/api/postings/{cohere['id']}/track").status_code == 409
    assert client.post("/api/postings/9999/track").status_code == 404

    # the tracked posting is recognised on the next scan through the tracker, not the DB
    li = next(p for p in new if p["source"] == "linkedin")
    client.post(f"/api/postings/{li['id']}/track")
    assert client.get("/api/tracker").json()["rows"][-1]["req"] == "LinkedIn 4458535812"
