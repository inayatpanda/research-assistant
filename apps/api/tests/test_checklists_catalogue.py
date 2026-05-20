"""Phase 20 (MP20) — Catalogue loader regression.

Pins the published item counts for the 12 shipped reporting guidelines so
a future edit can't silently delete or duplicate an item.
"""
from __future__ import annotations

import pytest

from research_api.services.checklists.catalogue import (
    all_keys,
    get_catalogue,
    list_catalogues,
)


# (key, expected item count)
EXPECTED: dict[str, int] = {
    "CONSORT_2010": 25,
    "PRISMA_2020": 27,
    "CHEERS_2022": 28,
    "STROBE_COHORT": 22,
    "STROBE_CASE_CONTROL": 22,
    "STROBE_CROSS_SECTIONAL": 22,
    "TRIPOD_AI": 27,
    "SPIRIT_2013": 33,
    "SQUIRE_2": 18,
    "CARE": 13,
    "AGREE_II": 23,
    "SAMPL": 30,
    "PRISMA_S": 16,
    "PRISMA_SCR": 22,
}


def test_all_published_catalogues_load() -> None:
    keys = set(all_keys())
    missing = set(EXPECTED) - keys
    assert not missing, f"missing catalogues: {missing}"


@pytest.mark.parametrize("key,count", list(EXPECTED.items()))
def test_catalogue_item_count_matches_canonical(key: str, count: int) -> None:
    cat = get_catalogue(key)
    assert cat is not None, f"catalogue {key} did not load"
    assert cat.item_count == count, (
        f"{key} expected {count} items, got {cat.item_count}"
    )


def test_catalogue_items_have_required_fields() -> None:
    for key in EXPECTED:
        cat = get_catalogue(key)
        assert cat is not None
        seen_ids: set[str] = set()
        for it in cat.items:
            assert it.id, f"{key}: item missing id"
            assert it.title, f"{key} item {it.id}: missing title"
            assert it.section_hint, f"{key} item {it.id}: missing section_hint"
            # Item ids must be unique within a catalogue.
            assert it.id not in seen_ids, f"{key}: duplicate id {it.id}"
            seen_ids.add(it.id)


def test_list_catalogues_returns_metadata_summary() -> None:
    cats = list_catalogues()
    assert len(cats) >= 12
    keys = {c["key"] for c in cats}
    for k in EXPECTED:
        assert k in keys
    for c in cats:
        assert {"key", "name", "description", "item_count", "default_section"}.issubset(
            c.keys()
        )
        assert c["item_count"] > 0


def test_get_catalogue_returns_none_for_unknown_key() -> None:
    assert get_catalogue("NOT_A_REAL_CHECKLIST") is None


def test_legacy_cheers_alias_remains_for_back_compat() -> None:
    """The MP18 stub exposed CHECKLISTS['cheers_2022']; older callers depend on it."""
    from research_api.services.checklists.catalogue import CHECKLISTS, CHEERS_2022

    assert "cheers_2022" in CHECKLISTS
    assert CHEERS_2022 is not None
    assert len(CHECKLISTS["cheers_2022"]["items"]) == 28
