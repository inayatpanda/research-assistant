"""Phase 16 (MP16) — Figure & table auto-numbering by first in-text reference.

Numbering is recomputed (not stored as an authoritative source-of-truth) any
time a manuscript section is edited or a figure is reordered. Output is a
``{id -> number}`` map; the caller is responsible for persistence if it
needs to mirror the result back to a database column.

Conventions:
    * Figures referenced via ``<figref id="...">`` or ``[Figure N]``-style
      placeholders in section content are numbered in *first-mention* order.
    * Figures with no in-text reference get higher numbers than referenced
      figures, sorted by their stored ``figure_number`` (legacy order).
    * Tables follow the same rules with ``<tableref id="...">``.

These are PURE FUNCTIONS — no DB, no side effects.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Protocol


# Match `<figref id="..." />`, `<figref id="..."></figref>`, or
# `[Figure: id="..."]` placeholders.
_FIGREF_RE = re.compile(
    r"""<figref\b[^>]*\bid\s*=\s*["']([^"']+)["'][^>]*/?>""",
    re.IGNORECASE,
)
_TABLEREF_RE = re.compile(
    r"""<tableref\b[^>]*\bid\s*=\s*["']([^"']+)["'][^>]*/?>""",
    re.IGNORECASE,
)


class _FigureLike(Protocol):
    id: str
    figure_number: int


class _SectionLike(Protocol):
    section_name: str
    content: str


# Canonical section order — referenced figures are numbered in the order
# they appear when reading the manuscript top-to-bottom.
_SECTION_ORDER = [
    "Abstract",
    "Introduction",
    "Methods",
    "Methodology",
    "Results",
    "Discussion",
    "Conclusion",
]


@dataclass(frozen=True)
class NumberingResult:
    """Numbering map + ordered ids for downstream callers."""

    numbers: dict[str, int]
    ordered_ids: list[str]


def _ordered_sections(
    sections: Iterable[_SectionLike],
) -> list[_SectionLike]:
    """Stable-sort sections by canonical order, with unknown sections last."""
    section_list = list(sections)
    rank: dict[str, int] = {name: i for i, name in enumerate(_SECTION_ORDER)}

    def key(s: _SectionLike) -> tuple[int, str]:
        return (rank.get(s.section_name, len(_SECTION_ORDER)), s.section_name)

    return sorted(section_list, key=key)


def _first_reference_order(
    sections: Iterable[_SectionLike], pattern: re.Pattern[str]
) -> list[str]:
    """Walk sections in canonical order; return ids in first-mention order."""
    seen: list[str] = []
    seen_set: set[str] = set()
    for s in _ordered_sections(sections):
        for m in pattern.finditer(s.content or ""):
            ref_id = m.group(1).strip()
            if not ref_id or ref_id in seen_set:
                continue
            seen_set.add(ref_id)
            seen.append(ref_id)
    return seen


def _number_by_first_mention(
    items: list[_FigureLike],
    sections: Iterable[_SectionLike],
    pattern: re.Pattern[str],
) -> NumberingResult:
    by_id = {x.id: x for x in items}
    referenced = _first_reference_order(sections, pattern)
    # Drop ids that are referenced but don't exist (stale refs in prose).
    referenced = [rid for rid in referenced if rid in by_id]
    # Items with no in-text reference: sort by stored figure_number to keep
    # legacy ordering stable. NULL/0 figure_numbers sort last.
    unreferenced = [
        x for x in items if x.id not in set(referenced)
    ]
    unreferenced_sorted = sorted(
        unreferenced,
        key=lambda x: (x.figure_number if x.figure_number else 1_000_000, x.id),
    )
    ordered_ids = referenced + [x.id for x in unreferenced_sorted]
    numbers = {fid: i + 1 for i, fid in enumerate(ordered_ids)}
    return NumberingResult(numbers=numbers, ordered_ids=ordered_ids)


def assign_figure_numbers(
    figures: list[_FigureLike],
    manuscript_sections: Iterable[_SectionLike],
) -> NumberingResult:
    """Assign Figure 1..N by first in-text reference order.

    Returns a ``{figure_id -> 1-based number}`` map. Figures with no
    in-text reference are appended in their legacy ``figure_number`` order.
    """
    return _number_by_first_mention(figures, manuscript_sections, _FIGREF_RE)


def assign_table_numbers(
    tables: list[_FigureLike],
    manuscript_sections: Iterable[_SectionLike],
) -> NumberingResult:
    """Assign Table 1..N by first in-text reference order.

    ``tables`` uses the same shape as ``figures`` — any object with an ``id``
    and a numeric ``figure_number`` (or equivalent ordinal). Tables are
    typically tracked separately in the frontend but follow identical
    numbering semantics. Reuses the figure-style helper for parity.
    """
    return _number_by_first_mention(tables, manuscript_sections, _TABLEREF_RE)


__all__ = [
    "NumberingResult",
    "assign_figure_numbers",
    "assign_table_numbers",
]
