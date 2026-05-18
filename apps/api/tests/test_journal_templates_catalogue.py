"""Phase 8.7 — Journal template catalogue tests."""
from __future__ import annotations

import re

from research_api.services.journal_templates.catalogue import (
    JOURNALS,
    get_template,
    list_templates,
)


def test_catalogue_has_eight_journals() -> None:
    assert len(JOURNALS) == 8


def test_catalogue_keys_match_pattern() -> None:
    pattern = re.compile(r"^[a-z0-9][a-z0-9-]*$")
    for key in JOURNALS:
        assert pattern.match(key), f"bad key: {key}"


def test_every_template_has_required_sections_nonempty() -> None:
    for t in list_templates():
        assert t.required_sections


def test_every_template_sum_of_section_caps_geq_total_or_warns() -> None:
    """Sum of per-section caps should be >= total cap so the chip math is sensible.

    The plan permits a warning if not — we assert the design constraint.
    """
    for t in list_templates():
        s = sum(t.max_words_by_section.values())
        assert s >= t.max_total_words, (
            f"{t.key}: sum of section caps ({s}) < max_total_words ({t.max_total_words})"
        )


def test_get_template_returns_none_on_unknown_key() -> None:
    assert get_template("nope") is None


def test_get_template_returns_match_for_known_key() -> None:
    t = get_template("jbjs")
    assert t is not None and t.label.startswith("JBJS")
