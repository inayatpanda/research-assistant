"""APA 7 bibliography entry — golden-string regression anchors."""
from dataclasses import dataclass, field

import pytest

from research_api.services.citation_format import apa7_entry, format_entry


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


def test_apa7_canonical_two_authors_full():
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
    assert apa7_entry(a) == (
        "Doe, J., & Smith, J. (2024). Anterior approach. "
        "J Orthop Res, 42(3), 100–110. https://doi.org/10.1234/jor.42.3.100"
    )


def test_apa7_single_author():
    a = A(title="Solo work", authors=["John Doe"], year=2020, journal="J", volume="1", pages="1-2")
    assert apa7_entry(a) == "Doe, J. (2020). Solo work. J, 1, 1–2."


def test_apa7_three_authors_uses_serial_ampersand():
    a = A(
        title="Trio",
        authors=["Jane Doe", "John Smith", "Alice Lee"],
        year=2024,
        journal="J",
    )
    assert apa7_entry(a) == "Doe, J., Smith, J., & Lee, A. (2024). Trio. J."


def test_apa7_two_authors_uses_ampersand():
    a = A(title="Duo", authors=["Jane Doe", "John Smith"], year=2024, journal="J")
    assert apa7_entry(a) == "Doe, J., & Smith, J. (2024). Duo. J."


def test_apa7_21_authors_uses_ellipsis_then_last():
    authors = [f"F{i} Last{i}" for i in range(1, 22)]
    a = A(title="Mega", authors=authors, year=2024, journal="J")
    out = apa7_entry(a)
    # First 19 listed then ", ... LastN, F." then last author
    assert out.startswith("Last1, F., Last2, F., Last3, F., Last4, F., Last5, F., Last6, F., Last7, F., Last8, F., Last9, F., Last10, F., Last11, F., Last12, F., Last13, F., Last14, F., Last15, F., Last16, F., Last17, F., Last18, F., Last19, F., ... Last21, F.")
    assert " (2024). Mega. J." in out


def test_apa7_no_doi_omits_doi_suffix():
    a = A(title="No doi", authors=["John Doe"], year=2024, journal="J")
    out = apa7_entry(a)
    assert "https://doi.org" not in out
    assert "doi:" not in out


def test_apa7_no_year_uses_nd():
    a = A(title="Undated", authors=["John Doe"], journal="J")
    assert apa7_entry(a) == "Doe, J. (n.d.). Undated. J."


def test_apa7_missing_volume_only_journal_and_pages():
    a = A(title="X", authors=["John Doe"], year=2024, journal="J", pages="10-20")
    assert apa7_entry(a) == "Doe, J. (2024). X. J, 10–20."


def test_apa7_empty_authors_uses_anonymous():
    a = A(title="X", authors=[], year=2024, journal="J")
    assert apa7_entry(a) == "Anonymous. (2024). X. J."


def test_apa7_via_format_entry_dispatch():
    a = A(title="T", authors=["John Doe"], year=2024, journal="J")
    assert format_entry(a, style="apa") == apa7_entry(a)


def test_apa7_title_trailing_period_stripped():
    a = A(title="Already period.", authors=["John Doe"], year=2024, journal="J")
    out = apa7_entry(a)
    assert "Already period." in out
    assert "Already period.." not in out
