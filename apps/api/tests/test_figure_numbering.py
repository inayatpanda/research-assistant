"""MP16 — Figure & table auto-numbering by first in-text reference order."""
from __future__ import annotations

from dataclasses import dataclass

from research_api.services.figures.numbering import (
    assign_figure_numbers,
    assign_table_numbers,
)


@dataclass
class Fig:
    id: str
    figure_number: int


@dataclass
class Sect:
    section_name: str
    content: str


def test_assign_figure_numbers_first_mention_order():
    """Figure mentioned first in Methods should get number 1 regardless of
    its stored figure_number."""
    figures = [
        Fig(id="fA", figure_number=1),
        Fig(id="fB", figure_number=2),
        Fig(id="fC", figure_number=3),
    ]
    sections = [
        Sect("Introduction", "Background context."),
        Sect("Methods", 'See <figref id="fC" /> for the protocol.'),
        Sect("Results", 'Outcomes shown in <figref id="fA" /> and <figref id="fB"/>.'),
    ]
    result = assign_figure_numbers(figures, sections)
    assert result.numbers == {"fC": 1, "fA": 2, "fB": 3}
    assert result.ordered_ids == ["fC", "fA", "fB"]


def test_assign_figure_numbers_unreferenced_appended_in_legacy_order():
    figures = [
        Fig(id="fA", figure_number=1),
        Fig(id="fB", figure_number=2),
        Fig(id="fC", figure_number=3),
        Fig(id="fD", figure_number=4),
    ]
    sections = [
        Sect("Results", 'See <figref id="fC" />.'),
    ]
    result = assign_figure_numbers(figures, sections)
    # fC referenced → 1; remaining sorted by figure_number → fA, fB, fD
    assert result.numbers == {"fC": 1, "fA": 2, "fB": 3, "fD": 4}


def test_assign_figure_numbers_reorder_updates_when_section_changes():
    figures = [
        Fig(id="fA", figure_number=1),
        Fig(id="fB", figure_number=2),
    ]
    before = assign_figure_numbers(
        figures,
        [Sect("Methods", '<figref id="fA"/>'), Sect("Results", '<figref id="fB"/>')],
    )
    after = assign_figure_numbers(
        figures,
        [Sect("Methods", '<figref id="fB"/>'), Sect("Results", '<figref id="fA"/>')],
    )
    assert before.numbers == {"fA": 1, "fB": 2}
    assert after.numbers == {"fB": 1, "fA": 2}


def test_assign_figure_numbers_no_figures_returns_empty():
    result = assign_figure_numbers([], [Sect("Methods", "no refs")])
    assert result.numbers == {}
    assert result.ordered_ids == []


def test_assign_table_numbers_uses_tableref_tag():
    tables = [
        Fig(id="tA", figure_number=1),
        Fig(id="tB", figure_number=2),
    ]
    sections = [
        Sect("Results", 'See <tableref id="tB"/> and then <tableref id="tA"/>.'),
    ]
    result = assign_table_numbers(tables, sections)
    assert result.numbers == {"tB": 1, "tA": 2}


def test_stale_figref_to_missing_figure_ignored():
    """A figref pointing at a deleted figure shouldn't crash or steal a
    number — it's silently skipped."""
    figures = [Fig(id="fA", figure_number=1)]
    sections = [Sect("Methods", '<figref id="ghost"/> then <figref id="fA"/>')]
    result = assign_figure_numbers(figures, sections)
    assert result.numbers == {"fA": 1}
