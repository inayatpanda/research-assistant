"""Harvard (Cite Them Right 11) bibliography entry — golden-string anchors."""
from dataclasses import dataclass, field

from research_api.services.citation_format import format_entry, harvard_entry


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


def test_harvard_canonical_two_authors_full():
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
    assert harvard_entry(a) == (
        "Doe, J. and Smith, J. (2024) 'Anterior approach', "
        "J Orthop Res, 42(3), pp. 100–110. doi:10.1234/jor.42.3.100"
    )


def test_harvard_single_author():
    a = A(title="Solo", authors=["John Doe"], year=2020, journal="J")
    assert harvard_entry(a) == "Doe, J. (2020) 'Solo', J."


def test_harvard_two_authors_uses_and():
    a = A(title="Duo", authors=["Jane Doe", "John Smith"], year=2024, journal="J")
    assert harvard_entry(a) == "Doe, J. and Smith, J. (2024) 'Duo', J."


def test_harvard_three_plus_uses_et_al():
    a = A(
        title="Trio",
        authors=["Jane Doe", "John Smith", "Alice Lee"],
        year=2024,
        journal="J",
    )
    assert harvard_entry(a) == "Doe, J. et al. (2024) 'Trio', J."


def test_harvard_no_doi():
    a = A(title="No doi", authors=["John Doe"], year=2024, journal="J", volume="1", pages="1-2")
    assert harvard_entry(a) == "Doe, J. (2024) 'No doi', J, 1, pp. 1–2."


def test_harvard_no_year_uses_nd():
    a = A(title="Undated", authors=["John Doe"], journal="J")
    assert harvard_entry(a) == "Doe, J. (n.d.) 'Undated', J."


def test_harvard_missing_volume_only_pages():
    a = A(title="X", authors=["John Doe"], year=2024, journal="J", pages="10-20")
    assert harvard_entry(a) == "Doe, J. (2024) 'X', J, pp. 10–20."


def test_harvard_empty_authors_uses_anon():
    a = A(title="X", authors=[], year=2024, journal="J")
    assert harvard_entry(a) == "Anon. (2024) 'X', J."


def test_harvard_via_format_entry_dispatch():
    a = A(title="T", authors=["John Doe"], year=2024, journal="J")
    assert format_entry(a, style="harvard") == harvard_entry(a)


def test_harvard_volume_with_issue_no_pages():
    a = A(title="X", authors=["John Doe"], year=2024, journal="J", volume="42", issue="3")
    assert harvard_entry(a) == "Doe, J. (2024) 'X', J, 42(3)."
