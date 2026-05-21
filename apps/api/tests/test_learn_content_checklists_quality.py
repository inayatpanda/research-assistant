"""Phase 5b — Content quality regression for the reporting checklists.

Each canonical checklist has a published item count. We avoid counting
exact ``- [ ]`` markers (brittle when prose is re-formatted) and instead
require the entry body to (a) contain the canonical count somewhere in
the prose and (b) include enough actual checklist lines to be a working
reference, never below 80% of the canonical count.
"""
from __future__ import annotations

import re

from research_api.learn.loader import _reset_cache, load_all_checklists


# Canonical published item counts for each checklist.
EXPECTED_ITEM_COUNTS: dict[str, int] = {
    "consort": 25,
    "strobe": 22,
    "prisma": 27,
    "care": 13,
    "squire": 18,
    "coreq": 32,
    "srqr": 21,
    "tripod": 22,
    "cheers": 28,
    "stard": 30,
    "moose": 35,
    "arrive": 21,
}

# We accept body-counted items down to this fraction of the canonical
# count to absorb sub-item collapsing (e.g. 1a + 1b counted as 1 line).
_MIN_FRACTION = 0.80

_CHECKBOX_RE = re.compile(r"^\s*-\s*\[\s\]", re.MULTILINE)


def setup_function() -> None:
    _reset_cache()


def test_every_checklist_mentions_its_canonical_item_count() -> None:
    """The body text should explicitly reference its published item count."""
    missing: list[tuple[str, int]] = []
    for entry in load_all_checklists():
        expected = EXPECTED_ITEM_COUNTS[entry.slug]
        # Look for "(N items)" or " N items" or " N item" in the body.
        pat = re.compile(rf"\b{expected}\b\s*(?:item|items|sub-?item)", re.IGNORECASE)
        if not pat.search(entry.body_md):
            missing.append((entry.slug, expected))
    assert not missing, (
        f"checklists not referencing their canonical item count: {missing}"
    )


def test_every_checklist_has_enough_actionable_items() -> None:
    """Each entry should include at least ~80% of its canonical item count
    as actual ``- [ ]`` lines so the page is usable as a working reference."""
    short: list[tuple[str, int, int]] = []
    for entry in load_all_checklists():
        expected = EXPECTED_ITEM_COUNTS[entry.slug]
        actual = len(_CHECKBOX_RE.findall(entry.body_md))
        min_required = int(expected * _MIN_FRACTION)
        if actual < min_required:
            short.append((entry.slug, actual, expected))
    assert not short, (
        f"checklists below {_MIN_FRACTION:.0%} of canonical item count: {short}"
    )
