"""Phase 15 (MP15) — pure helper tests for living-review."""
from __future__ import annotations

from research_api.services.review.living import diff_new_hits


def test_diff_new_hits_returns_only_new_in_fresh_order() -> None:
    prior = {"100", "200"}
    fresh = ["200", "300", "400", "100"]
    assert diff_new_hits(prior, fresh) == ["300", "400"]


def test_diff_new_hits_empty_prior_returns_all_unique() -> None:
    prior: set[str] = set()
    fresh = ["1", "2", "3"]
    assert diff_new_hits(prior, fresh) == ["1", "2", "3"]


def test_diff_new_hits_dedupes_within_fresh() -> None:
    prior = {"x"}
    fresh = ["a", "b", "a", "b", "c"]
    assert diff_new_hits(prior, fresh) == ["a", "b", "c"]


def test_diff_new_hits_drops_empty_strings() -> None:
    assert diff_new_hits(set(), ["", "a", ""]) == ["a"]


def test_diff_new_hits_no_new_returns_empty() -> None:
    assert diff_new_hits({"a", "b"}, ["a", "b"]) == []
