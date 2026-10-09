"""BM25, RRF and the rank_jobs wrapper — pure functions, no network, no model."""

from __future__ import annotations

import pytest

from jobs_mcp import rank


def test_tokenize_keeps_tech_tokens_and_drops_stopwords():
    toks = rank.tokenize("We use C++, C# and Node.js with the .NET stack for our team")
    assert {"c++", "c#", "node.js", "net", "stack"} <= set(toks)
    assert "the" not in toks and "team" not in toks


def test_bm25_prefers_docs_with_rare_query_terms():
    docs = ["python python backend", "python unity gameplay", "java backend"]
    s = rank.bm25("unity gameplay", docs)
    assert s[1] > s[0] and s[1] > s[2]
    assert s[0] == 0.0


def test_bm25_empty():
    assert rank.bm25("x", []) == []


def test_rrf_combines_rankings():
    a = [3.0, 2.0, 1.0]  # ranks 1, 2, 3
    b = [1.0, 2.0, 3.0]  # ranks 3, 2, 1
    fused = rank.rrf(a, b)
    assert fused[0] == pytest.approx(fused[2])
    assert fused[1] == pytest.approx(2 / (rank.RRF_K + 2))


def test_rank_jobs_title_weight_and_fields(monkeypatch):
    monkeypatch.setenv("JOBS_MCP_DENSE", "0")
    jobs = [
        {"id": "a", "title": "Data Analyst", "description": "Some agent work here."},
        {"id": "b", "title": "Agent Engineer", "description": "Build things."},
    ]
    ranked, method = rank.rank_jobs("agent", jobs)
    assert method == "bm25"
    assert [j["id"] for j in ranked] == ["b", "a"]
    assert ranked[0]["match_terms"] == ["agent"]
    assert "match_score" not in jobs[0]  # inputs untouched


def test_rank_jobs_falls_back_when_dense_fails(monkeypatch):
    monkeypatch.setattr(rank, "dense_available", lambda: True)

    def boom(*_a, **_k):
        raise RuntimeError("no model")

    monkeypatch.setattr(rank, "dense", boom)
    ranked, method = rank.rank_jobs("agent", [{"id": "a", "title": "Agent"}])
    assert method == "bm25" and ranked[0]["id"] == "a"


def test_rank_jobs_uses_rrf_when_dense_available(monkeypatch):
    monkeypatch.setattr(rank, "dense_available", lambda: True)
    monkeypatch.setattr(rank, "dense", lambda q, docs: [0.0, 1.0])  # dense prefers b, BM25 prefers a
    jobs = [{"id": "a", "title": "agent agent"}, {"id": "b", "title": "agent"}]
    ranked, method = rank.rank_jobs("agent", jobs)
    assert method == "bm25+dense"
    assert ranked[0]["match_score"] == pytest.approx(ranked[1]["match_score"])
