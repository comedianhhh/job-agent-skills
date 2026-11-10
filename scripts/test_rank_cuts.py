"""Tests for rank-cuts.py. Run: python scripts/test_rank_cuts.py (or pytest scripts/)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("rank_cuts", Path(__file__).with_name("rank-cuts.py"))
rc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rc)

JD = "Backend engineer: Go services, PostgreSQL, Kafka event pipelines, webhooks, on-call for payments APIs."
OLD_BUT_RELEVANT = "Built Kafka event pipelines and Go webhook consumers for payments APIs at a fintech in 2019 era."
RECENT_IRRELEVANT = "Animated the Unity character rig with blendshapes and tuned facial expressions for the avatar."
DUPLICATE_A = "Wrote PostgreSQL migrations and indexes for the billing service, cutting query time on reports."
DUPLICATE_B = "Wrote PostgreSQL migrations and indexes for the billing service, cutting query time on exports."


def test_irrelevant_bullet_is_cut_first_even_when_recent():
    rows = rc.rank([OLD_BUT_RELEVANT, RECENT_IRRELEVANT, DUPLICATE_A], JD)
    assert rows[0]["bullet"] == RECENT_IRRELEVANT
    assert rows[-1]["bullet"] == OLD_BUT_RELEVANT
    assert rows[0]["relevance"] == 0 and rows[-1]["relevance"] == 1


def test_near_duplicates_lose_uniqueness():
    rows = {r["bullet"]: r for r in rc.rank([DUPLICATE_A, DUPLICATE_B, OLD_BUT_RELEVANT], JD)}
    assert rows[DUPLICATE_A]["uniqueness"] < 0.3 < rows[OLD_BUT_RELEVANT]["uniqueness"]


def test_letter_dependency_protects_a_line():
    letter = "At Acme I animated the Unity character rig with blendshapes for the avatar."
    plain = rc.rank([RECENT_IRRELEVANT, DUPLICATE_A], "unrelated query words only")
    leaned = rc.rank([RECENT_IRRELEVANT, DUPLICATE_A], "unrelated query words only", letter)
    score = {r["bullet"]: r["score"] for r in leaned}
    assert score[RECENT_IRRELEVANT] > next(r["score"] for r in plain if r["bullet"] == RECENT_IRRELEVANT)


def test_letter_body_skips_the_header():
    assert rc.letter_body("Name\nphone\n---\nBody text").strip() == "Body text"


def test_empty_resume():
    assert rc.rank([], JD) == []


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
