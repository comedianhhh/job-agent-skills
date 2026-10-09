"""Rank scanned postings against a profile query: BM25, plus dense embeddings when available.

Keyword filters (`include_regex` etc.) decide what is *eligible*; this module decides what is
*first*. BM25 is pure Python and always on. When the optional `fastembed` extra is installed
(`pip install "jobs-mcp[rank]"`) a small local embedding model scores the same texts and the two
rankings are merged with Reciprocal Rank Fusion, so neither score scale has to be calibrated.
Set JOBS_MCP_DENSE=0 to force BM25 only.
"""

from __future__ import annotations

import math
import os
import re
from collections import Counter
from typing import Any

# Keeps tech tokens whole: c++, c#, node.js, .net, gpt-4o is split on '-' on purpose.
_TOKEN = re.compile(r"[a-z0-9.#+]*[a-z0-9#+]")
_STOP = frozenset(
    "a an and are as at be by for from has have in is it its of on or our that the this to we will with "
    "you your they their who what when where how all any can do not but if into more most other some "
    "such than then there these those very about across using use work working team role job".split()
)
TITLE_WEIGHT = 3  # a title term counts like three body occurrences
RRF_K = 60
DENSE_MODEL = "BAAI/bge-small-en-v1.5"

_dense_model: Any = None


def tokenize(text: str) -> list[str]:
    return [t.lstrip(".") for t in _TOKEN.findall(text.lower()) if t not in _STOP and len(t) > 1]


def job_text(job: dict[str, Any]) -> str:
    title = job.get("title") or ""
    return " ".join([title] * TITLE_WEIGHT + [job.get("description") or ""])


def bm25(query: str, docs: list[str], k1: float = 1.5, b: float = 0.75) -> list[float]:
    """Okapi BM25 score of every doc for `query`."""
    toks = [tokenize(d) for d in docs]
    n = len(toks)
    if n == 0:
        return []
    avgdl = sum(len(t) for t in toks) / n or 1.0
    df: Counter[str] = Counter()
    for t in toks:
        df.update(set(t))
    q = set(tokenize(query))
    scores: list[float] = []
    for t in toks:
        tf = Counter(t)
        dl = len(t)
        s = 0.0
        for term in q:
            f = tf.get(term, 0)
            if not f:
                continue
            idf = math.log(1 + (n - df[term] + 0.5) / (df[term] + 0.5))
            s += idf * f * (k1 + 1) / (f + k1 * (1 - b + b * dl / avgdl))
        scores.append(s)
    return scores


def dense_available() -> bool:
    if os.environ.get("JOBS_MCP_DENSE", "1") == "0":
        return False
    try:
        import fastembed  # noqa: F401
    except ImportError:
        return False
    return True


def dense(query: str, docs: list[str]) -> list[float]:
    """Cosine similarity of every doc to `query` with a local embedding model (downloads once, ~130 MB)."""
    global _dense_model
    from fastembed import TextEmbedding

    if _dense_model is None:
        _dense_model = TextEmbedding(DENSE_MODEL)
    qv = next(iter(_dense_model.query_embed([query])))
    out: list[float] = []
    for dv in _dense_model.passage_embed(docs):
        num = float(sum(a * b for a, b in zip(qv, dv, strict=True)))
        den = math.sqrt(float(sum(a * a for a in qv))) * math.sqrt(float(sum(b * b for b in dv))) or 1.0
        out.append(num / den)
    return out


def _ranks(scores: list[float]) -> list[int]:
    order = sorted(range(len(scores)), key=lambda i: -scores[i])
    r = [0] * len(scores)
    for pos, i in enumerate(order):
        r[i] = pos + 1
    return r


def rrf(*score_lists: list[float], k: int = RRF_K) -> list[float]:
    """Reciprocal Rank Fusion: sum of 1 / (k + rank) across rankings."""
    fused = [0.0] * len(score_lists[0])
    for scores in score_lists:
        for i, r in enumerate(_ranks(scores)):
            fused[i] += 1.0 / (k + r)
    return fused


def rank_jobs(query: str, jobs: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str]:
    """Return `jobs` sorted best-first, each with `match_score` and `match_terms`, plus the method used."""
    if not jobs:
        return [], "bm25"
    texts = [job_text(j) for j in jobs]
    lexical = bm25(query, texts)
    method = "bm25"
    final = lexical
    if dense_available():
        try:
            final = rrf(lexical, dense(query, texts))
            method = "bm25+dense"
        except Exception:  # model download or runtime failure: BM25 alone is still a ranking
            final = lexical
    q = set(tokenize(query))
    out = []
    for j, text, score in zip(jobs, texts, final, strict=True):
        d = dict(j)
        d["match_score"] = round(score, 4)
        d["match_terms"] = sorted(q & set(tokenize(text)))
        out.append(d)
    out.sort(key=lambda d: -d["match_score"])
    return out, method
