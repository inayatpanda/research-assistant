"""Phase 5c — Walkthrough loader regression tests."""
from __future__ import annotations

from research_api.learn.loader import (
    WALKTHROUGHS_DIR,
    WalkthroughEntry,
    _reset_cache,
    load_all_walkthroughs,
)


EXPECTED_WALKTHROUGH_COUNT = 4
MIN_WORD_COUNT = 1500
MIN_CONCEPT_REFS = 5


def setup_function() -> None:
    _reset_cache()


def test_loader_returns_exactly_four_walkthroughs() -> None:
    entries = load_all_walkthroughs()
    assert len(entries) == EXPECTED_WALKTHROUGH_COUNT
    assert WALKTHROUGHS_DIR.exists()
    expected_slugs = {
        "systematic-review-from-scratch",
        "rct-write-up",
        "observational-study-write-up",
        "meta-analysis-walkthrough",
    }
    actual = {e.slug for e in entries}
    assert actual == expected_slugs


def test_every_walkthrough_has_min_word_count() -> None:
    entries = load_all_walkthroughs()
    for e in entries:
        assert isinstance(e, WalkthroughEntry)
        word_count = len(e.body_md.split())
        assert word_count >= MIN_WORD_COUNT, (
            f"{e.slug}: only {word_count} words (need {MIN_WORD_COUNT}+)"
        )


def test_every_walkthrough_references_at_least_five_concepts() -> None:
    entries = load_all_walkthroughs()
    for e in entries:
        assert len(e.related_concepts) >= MIN_CONCEPT_REFS, (
            f"{e.slug}: only {len(e.related_concepts)} concepts "
            f"(need {MIN_CONCEPT_REFS}+)"
        )
        # And the frontmatter fields are populated.
        assert e.title
        assert e.study_type
        assert e.estimated_reading_minutes >= 1
        assert e.sections, f"{e.slug}: missing sections list"


def test_walkthrough_domains_cover_ortho_med_surg() -> None:
    """The 4 walkthroughs should span the three worked-example domains."""
    entries = load_all_walkthroughs()
    domains = {e.worked_example_domain for e in entries}
    assert {"orthopaedics", "medicine", "surgery"}.issubset(domains)
