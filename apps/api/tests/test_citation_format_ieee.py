"""IEEE bibliography entry — golden-string anchors.

The function returns the post-`[N] ` portion only; the caller prepends `[N] `.
"""
from dataclasses import dataclass, field

from research_api.services.citation_format import format_entry, ieee_entry


@dataclass
class A:
    title: str | None = None
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    journal: str | None = None
    doi: str | None = None
    volume: str | None = None
    issue: str | None = None
    pages: str | None = None


def test_ieee_canonical_two_authors_full():
    a = A(
        title="Anterior approach",
        authors=["Jane Doe", "John Smith"],
        year=2024,
        journal="J Orthop Res",
        volume="42",
        issue="3",
        pages="100-110",
        doi="10.1234/jor.42.3.100",
    )
    assert ieee_entry(a) == (
        'J. Doe and J. Smith, "Anterior approach," J Orthop Res, '
        "vol. 42, no. 3, pp. 100–110, 2024, doi: 10.1234/jor.42.3.100."
    )


def test_ieee_single_author():
    a = A(title="Solo", authors=["John Doe"], year=2020, journal="J")
    assert ieee_entry(a) == 'J. Doe, "Solo," J, 2020.'


def test_ieee_three_authors_uses_and_before_last():
    a = A(
        title="Trio",
        authors=["Jane Doe", "John Smith", "Alice Lee"],
        year=2024,
        journal="J",
    )
    assert ieee_entry(a) == 'J. Doe, J. Smith, and A. Lee, "Trio," J, 2024.'


def test_ieee_four_plus_uses_et_al():
    a = A(
        title="Quad",
        authors=["Jane Doe", "John Smith", "Alice Lee", "Bob King"],
        year=2024,
        journal="J",
    )
    assert ieee_entry(a) == 'J. Doe et al., "Quad," J, 2024.'


def test_ieee_no_doi():
    a = A(title="X", authors=["John Doe"], year=2024, journal="J", volume="1", pages="1-2")
    assert ieee_entry(a) == 'J. Doe, "X," J, vol. 1, pp. 1–2, 2024.'


def test_ieee_no_year_omits_year_segment():
    a = A(title="Undated", authors=["John Doe"], journal="J")
    assert ieee_entry(a) == 'J. Doe, "Undated," J.'


def test_ieee_empty_authors_uses_anonymous():
    a = A(title="X", authors=[], year=2024, journal="J")
    assert ieee_entry(a) == 'Anonymous, "X," J, 2024.'


def test_ieee_via_format_entry_dispatch():
    a = A(title="T", authors=["John Doe"], year=2024, journal="J")
    assert format_entry(a, style="ieee") == ieee_entry(a)


def test_ieee_volume_no_issue_with_pages():
    a = A(title="X", authors=["John Doe"], year=2024, journal="J", volume="42", pages="10-20")
    assert ieee_entry(a) == 'J. Doe, "X," J, vol. 42, pp. 10–20, 2024.'
