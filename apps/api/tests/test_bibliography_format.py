from dataclasses import dataclass

from research_api.services.citation_format import bibliography_entry


@dataclass
class A:
    title: str | None = None
    authors: list[str] | None = None
    year: int | None = None
    journal: str | None = None
    doi: str | None = None
    volume: str | None = None
    issue: str | None = None
    pages: str | None = None

    def __post_init__(self) -> None:
        if self.authors is None:
            self.authors = []


def test_vancouver_full_entry():
    a = A(
        title="Anterior approach in total hip arthroplasty",
        authors=["John Doe", "Jane Smith"],
        year=2024,
        journal="J Orthop Res",
        volume="42",
        issue="3",
        pages="100-110",
        doi="10.1234/abc",
    )
    out = bibliography_entry(a, number=1)
    assert out.startswith("1. ")
    assert "Doe J, Smith J." in out
    assert "Anterior approach in total hip arthroplasty." in out
    assert "J Orthop Res." in out
    assert "2024;42(3):100-110." in out
    assert "doi:10.1234/abc" in out


def test_single_author_no_journal():
    a = A(title="Solo work", authors=["John Doe"], year=2020)
    out = bibliography_entry(a, number=2)
    assert "Doe J." in out
    assert "Solo work." in out
    assert "2020." in out


def test_et_al_for_seven_plus_authors():
    a = A(
        title="Big collab",
        authors=[f"First{i} Last{i}" for i in range(8)],
        year=2024,
    )
    out = bibliography_entry(a)
    # First 6 listed, then 'et al.'
    assert out.count("et al.") == 1


def test_no_year_uses_nd():
    a = A(title="Undated", authors=["John Doe"])
    out = bibliography_entry(a, number=3)
    assert "n.d." in out


def test_no_doi_no_doi_line():
    a = A(title="No doi here", authors=["John Doe"], year=2023)
    out = bibliography_entry(a)
    assert "doi:" not in out


def test_no_authors_falls_back_to_anonymous():
    a = A(title="Anonymous study", authors=[], year=2021)
    out = bibliography_entry(a)
    assert "Anonymous." in out
