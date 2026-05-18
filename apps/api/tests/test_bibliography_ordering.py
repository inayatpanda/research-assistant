"""Per-style bibliography ordering (BUG #14).

Vancouver / IEEE: first-citation-of-appearance (numeric inline → numeric bib).
APA / Harvard: alphabetical by first author's surname (case-insensitive),
ties broken by year ascending then title.
"""
from dataclasses import dataclass, field

import pytest

from research_api.services.export.bibliography import build_bibliography


@dataclass
class Section:
    section_name: str
    content: str


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


def _sections(by_name: dict[str, str]) -> list[Section]:
    return [Section(section_name=name, content=html) for name, html in by_name.items()]


# Three articles whose first authors' surnames sort: Brown < Patel < Smith.
# Cited in REVERSE alphabetical order so the test can distinguish.
ZEBRA = A(title="Zebras of the savanna", authors=["Lisa Smith"], year=2024, journal="J Zoo")
PARK = A(title="Park life", authors=["Raj Patel"], year=2022, journal="J Urb")
APPLE = A(title="Apples", authors=["Anna Brown"], year=2021, journal="J Bot")

ARTICLES = {"z1": ZEBRA, "p1": PARK, "b1": APPLE}
SECTIONS_REVERSED = _sections({
    "Introduction": "[CITE_z1] [CITE_p1] [CITE_b1]",
})


@pytest.mark.parametrize("style", ["vancouver", "ieee"])
def test_vancouver_ieee_keep_first_citation_order(style):
    """Numbered styles keep the first-citation order they always had."""
    out = build_bibliography(
        articles_by_id=ARTICLES, sections=SECTIONS_REVERSED, style=style,
    )
    assert [e.article_id for e in out] == ["z1", "p1", "b1"]
    assert [e.number for e in out] == [1, 2, 3]


@pytest.mark.parametrize("style", ["apa", "harvard"])
def test_apa_harvard_alphabetical_by_first_author(style):
    """APA + Harvard alphabetise by first author's surname."""
    out = build_bibliography(
        articles_by_id=ARTICLES, sections=SECTIONS_REVERSED, style=style,
    )
    # Brown, Patel, Smith — alphabetical.
    assert [e.article_id for e in out] == ["b1", "p1", "z1"]


@pytest.mark.parametrize("style", ["apa", "harvard"])
def test_apa_harvard_alphabetical_is_case_insensitive(style):
    """Lowercased surname sorts identically to its capital form."""
    arts = {
        "x1": A(title="X", authors=["zoë lower"], year=2020),
        "x2": A(title="Y", authors=["Bob Capital"], year=2020),
    }
    sections = _sections({"Introduction": "[CITE_x1] [CITE_x2]"})
    out = build_bibliography(articles_by_id=arts, sections=sections, style=style)
    assert [e.article_id for e in out] == ["x2", "x1"]


@pytest.mark.parametrize("style", ["apa", "harvard"])
def test_apa_harvard_tie_break_by_year_then_title(style):
    """Same surname: year ASC, then title ASC."""
    arts = {
        "s1": A(title="Beta paper", authors=["Sam Smith"], year=2024),
        "s2": A(title="Alpha paper", authors=["Sam Smith"], year=2020),
        "s3": A(title="Gamma paper", authors=["Sam Smith"], year=2020),
    }
    # Cited s1 first so first-occurrence policy would put s1 first; alphabetical
    # must override.
    sections = _sections({"Introduction": "[CITE_s1] [CITE_s2] [CITE_s3]"})
    out = build_bibliography(articles_by_id=arts, sections=sections, style=style)
    # s2 (2020, Alpha) < s3 (2020, Gamma) < s1 (2024, Beta)
    assert [e.article_id for e in out] == ["s2", "s3", "s1"]


@pytest.mark.parametrize("style", ["apa", "harvard"])
def test_apa_harvard_missing_year_sorts_last(style):
    arts = {
        "n1": A(title="No year", authors=["Same Author"]),
        "y1": A(title="With year", authors=["Same Author"], year=2020),
    }
    sections = _sections({"Introduction": "[CITE_n1] [CITE_y1]"})
    out = build_bibliography(articles_by_id=arts, sections=sections, style=style)
    # 2020 < n.d. → y1 first
    assert [e.article_id for e in out] == ["y1", "n1"]


@pytest.mark.parametrize("style", ["apa", "harvard"])
def test_apa_harvard_empty_authors_sorts_to_anonymous_bucket(style):
    """An article with no authors should not crash the sort. We expect it to
    bucket to the end (empty surname < any letter)."""
    arts = {
        "a1": A(title="Anon", authors=[], year=2020),
        "z1": A(title="Z", authors=["Zoe Zed"], year=2020),
    }
    sections = _sections({"Introduction": "[CITE_a1] [CITE_z1]"})
    out = build_bibliography(articles_by_id=arts, sections=sections, style=style)
    # both styles: empty surname is lexicographically smallest, so "a1" first.
    assert [e.article_id for e in out] == ["a1", "z1"]


def test_vancouver_renumbers_in_first_citation_order():
    """Sanity check: existing Vancouver behaviour unchanged."""
    sections = _sections({
        "Methodology": "[CITE_z1]",
        "Introduction": "[CITE_p1]",  # appears in canonical order BEFORE Methodology
    })
    out = build_bibliography(articles_by_id=ARTICLES, sections=sections, style="vancouver")
    # Canonical: Introduction → Methodology, so p1 first.
    assert [e.article_id for e in out] == ["p1", "z1"]
    assert [e.number for e in out] == [1, 2]
