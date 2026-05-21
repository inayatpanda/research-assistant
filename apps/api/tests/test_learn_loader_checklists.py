"""Phase 5b — Reporting-checklist loader regression tests."""
from __future__ import annotations

from research_api.learn.loader import (
    CHECKLISTS_DIR,
    ChecklistEntry,
    _reset_cache,
    load_all_checklists,
)


EXPECTED_CHECKLIST_COUNT = 12


def setup_function() -> None:
    _reset_cache()


def test_loader_returns_exactly_twelve_checklists() -> None:
    entries = load_all_checklists()
    assert len(entries) == EXPECTED_CHECKLIST_COUNT
    assert CHECKLISTS_DIR.exists()


def test_every_checklist_slug_unique_and_has_required_fields() -> None:
    entries = load_all_checklists()
    slugs = [e.slug for e in entries]
    assert len(set(slugs)) == len(slugs), f"duplicate slugs in checklists: {slugs}"
    for e in entries:
        assert isinstance(e, ChecklistEntry)
        assert e.title
        assert e.reporting_standard, f"{e.slug}: missing reporting_standard"
        assert e.version, f"{e.slug}: missing version"
        assert e.official_url.startswith("http"), f"{e.slug}: bad official_url {e.official_url!r}"
        assert e.body_md
        assert e.worked_example_domain in {"orthopaedics", "medicine", "surgery"}


def test_expected_checklist_slugs_present() -> None:
    slugs = {e.slug for e in load_all_checklists()}
    expected = {
        "consort",
        "strobe",
        "prisma",
        "care",
        "squire",
        "coreq",
        "srqr",
        "tripod",
        "cheers",
        "stard",
        "moose",
        "arrive",
    }
    missing = expected - slugs
    assert not missing, f"checklists missing: {sorted(missing)}"
    # Every entry should declare a reporting_standard distinct from the others
    standards = {e.reporting_standard.upper() for e in load_all_checklists()}
    assert len(standards) == EXPECTED_CHECKLIST_COUNT
