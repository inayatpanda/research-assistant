"""Phase 5b — Submission loader regression tests."""
from __future__ import annotations

from research_api.learn.loader import (
    SUBMISSION_DIR,
    SubmissionEntry,
    _reset_cache,
    load_all_submission,
)


EXPECTED_SUBMISSION_COUNT = 11


def setup_function() -> None:
    _reset_cache()


def test_loader_returns_eleven_submission_topics() -> None:
    entries = load_all_submission()
    assert len(entries) == EXPECTED_SUBMISSION_COUNT
    assert SUBMISSION_DIR.exists()


def test_every_submission_entry_has_topic_field() -> None:
    entries = load_all_submission()
    topics: set[str] = set()
    families: set[str] = set()
    for e in entries:
        assert isinstance(e, SubmissionEntry)
        assert e.title
        assert e.topic, f"{e.slug}: missing topic"
        assert e.topic_family, f"{e.slug}: missing topic_family"
        assert e.body_md
        topics.add(e.topic)
        families.add(e.topic_family)
    assert len(topics) == EXPECTED_SUBMISSION_COUNT, f"non-unique topics: {topics}"
    # The 4 families described in the spec should all appear.
    assert {"planning", "writing", "submitting", "post-decision"}.issubset(families), (
        f"missing topic families; got {families}"
    )


def test_expected_submission_slugs_present() -> None:
    slugs = {e.slug for e in load_all_submission()}
    expected = {
        "picking-a-journal",
        "authorship-criteria",
        "cover-letter",
        "response-to-reviewers",
        "conflict-of-interest",
        "data-sharing-statements",
        "copyright-and-licensing",
        "preprints",
        "registration",
        "rejection-and-appeal",
        "reporting-guideline-selection",
    }
    missing = expected - slugs
    assert not missing, f"submission topics missing: {sorted(missing)}"
