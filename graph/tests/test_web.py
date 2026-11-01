"""The web API on the scripted model: a run streams node by node, parks at approve, resumes over HTTP."""

from __future__ import annotations

import json
import shutil

import pytest
from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import InMemorySaver
from test_graph import ACME, APPLY, CLEAN, FIXTURES, ROLE, FakeLLM

from apply_graph.state import SERDE
from apply_graph.web import create_app


def events(resp) -> list[dict]:
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("text/event-stream")
    return [json.loads(line[6:]) for line in resp.text.splitlines() if line.startswith("data: ")]


@pytest.fixture
def career(tmp_path):
    shutil.copy(FIXTURES / "facts.md", tmp_path / "facts.md")
    (tmp_path / ROLE.name).mkdir()
    shutil.copy(ROLE / "03-Job-Description.md", tmp_path / ROLE.name)
    return tmp_path


def test_run_streams_each_node_then_resumes_from_the_page(career):
    client = TestClient(create_app(FakeLLM(APPLY, ACME, CLEAN), career, InMemorySaver(serde=SERDE)))
    assert client.get("/api/jobs").json() == [{"id": ROLE.name}]

    evs = events(client.post("/api/runs", json={"job": ROLE.name}))
    assert [(e["type"], e.get("node")) for e in evs] == [
        ("start", None),
        ("step", "match"),
        ("step", "research_company"),
        ("step", "draft"),
        ("step", "trace_check"),
        ("interrupt", "__interrupt__"),
        ("end", None),
    ]
    # each step carries the state *after* its node, not one step behind
    steps = [e for e in evs if e["type"] == "step"]
    assert all(e["state"]["log"][-1].startswith(e["node"] + ":") for e in steps)
    assert [e["next"] for e in steps] == [["research_company"], ["draft"], ["trace_check"], ["approve"]]
    run_id, last = evs[0]["run_id"], evs[-1]
    assert last["next"] == ["approve"] and last["state"]["draft"] == CLEAN.body
    assert "job_text" not in last["state"]  # big inputs stay on the server
    assert client.get(f"/api/runs/{run_id}").json()["next"] == ["approve"]

    evs = events(client.post(f"/api/runs/{run_id}/resume", json={"approved": True}))
    assert evs[-1]["state"]["status"] == "READY" and evs[-1]["next"] == []
    assert (career / "_graph-runs" / run_id / "README.md").is_file()
    assert not (career / ROLE.name / "README.md").exists()  # the role folder is never written

    assert client.post(f"/api/runs/{run_id}/resume", json={"approved": True}).status_code == 409


@pytest.mark.parametrize("job", ["../etc", "_graph-runs", "missing-role"])
def test_start_only_accepts_role_folders(career, job):
    client = TestClient(create_app(FakeLLM(), career, InMemorySaver(serde=SERDE)))
    assert client.post("/api/runs", json={"job": job}).status_code == 404


def test_model_failure_is_reported_as_an_event(career):
    # an empty script makes the fake model raise IndexError on the first call
    client = TestClient(create_app(FakeLLM(), career, InMemorySaver(serde=SERDE)))
    evs = events(client.post("/api/runs", json={"job": ROLE.name}))
    assert evs[-1]["type"] == "error" and "IndexError" in evs[-1]["message"]
