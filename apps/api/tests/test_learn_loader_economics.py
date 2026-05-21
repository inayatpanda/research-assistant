"""Phase 5b — Economics loader regression tests."""
from __future__ import annotations

from research_api.learn.loader import (
    ECONOMICS_DIR,
    EconomicsEntry,
    _reset_cache,
    load_all_economics,
)


EXPECTED_ECONOMICS_COUNT = 10


def setup_function() -> None:
    _reset_cache()


def test_loader_returns_exactly_ten_economics_concepts() -> None:
    entries = load_all_economics()
    assert len(entries) == EXPECTED_ECONOMICS_COUNT
    assert ECONOMICS_DIR.exists()


def test_every_economics_entry_has_concept_family() -> None:
    entries = load_all_economics()
    families: set[str] = set()
    for e in entries:
        assert isinstance(e, EconomicsEntry)
        assert e.title
        assert e.concept_family, f"{e.slug}: missing concept_family"
        assert e.body_md
        families.add(e.concept_family)
    # We expect more than one family represented across the catalogue.
    assert len(families) >= 4, f"too few concept families: {families}"


def test_expected_economics_slugs_present() -> None:
    slugs = {e.slug for e in load_all_economics()}
    expected = {
        "cost-effectiveness-ratio",
        "incremental-cost-effectiveness-ratio",
        "quality-adjusted-life-year",
        "disability-adjusted-life-year",
        "net-monetary-benefit",
        "cost-utility-analysis",
        "cost-effectiveness-acceptability-curve",
        "markov-model",
        "probabilistic-sensitivity-analysis",
        "willingness-to-pay-threshold",
    }
    missing = expected - slugs
    assert not missing, f"economics concepts missing: {sorted(missing)}"
