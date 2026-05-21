"""Phase 5a — Learn loader regression tests.

Pins the count of shipped stat-test entries, validates that every entry
parses cleanly, slugs are unique, and the required frontmatter keys are
populated.
"""
from __future__ import annotations

from research_api.learn.loader import (
    STAT_TESTS_DIR,
    StatTestEntry,
    _reset_cache,
    load_all_stat_tests,
)


EXPECTED_COUNT = 27


def setup_function() -> None:
    _reset_cache()


def test_loader_returns_exactly_twenty_seven_entries() -> None:
    entries = load_all_stat_tests()
    assert len(entries) == EXPECTED_COUNT
    assert STAT_TESTS_DIR.exists()


def test_every_entry_has_required_fields() -> None:
    for e in load_all_stat_tests():
        assert isinstance(e, StatTestEntry)
        assert e.slug
        assert e.title
        assert e.family
        assert e.when_to_use
        assert e.worked_example_domain
        assert e.worked_example_dataset
        assert e.body_md
        # Each entry should declare at least one assumption.
        assert e.assumptions, f"{e.slug}: no assumptions declared"


def test_slugs_are_unique_and_kebab_case() -> None:
    entries = load_all_stat_tests()
    slugs = [e.slug for e in entries]
    assert len(set(slugs)) == len(slugs), "duplicate slugs detected"
    import re

    pat = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    for s in slugs:
        assert pat.match(s), f"slug {s!r} is not lower-kebab-case"


def test_worked_example_domains_split_evenly() -> None:
    """The brief requires ~9 ortho / 9 medicine / 9 surgery."""
    entries = load_all_stat_tests()
    counts: dict[str, int] = {}
    for e in entries:
        counts[e.worked_example_domain] = counts.get(e.worked_example_domain, 0) + 1
    # Allow modest deviation (>=7 in each) but the shipped catalogue is exactly 9/9/9.
    for domain in ("orthopaedics", "medicine", "surgery"):
        assert counts.get(domain, 0) >= 7, (
            f"domain {domain!r} under-represented: {counts}"
        )
    assert sum(counts.values()) == EXPECTED_COUNT
