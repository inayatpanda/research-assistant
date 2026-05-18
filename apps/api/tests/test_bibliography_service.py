"""Bibliography dedupe + ordering service."""
from dataclasses import dataclass, field

import pytest

from research_api.services.export.bibliography import (
    BibliographyEntry,
    build_bibliography,
    collect_used_article_ids_in_order,
)


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


def test_collect_empty_manuscript_returns_empty():
    assert collect_used_article_ids_in_order([]) == []


def test_collect_skips_sections_with_no_citations():
    sections = _sections({
        "Introduction": "<p>Plain prose with no citations.</p>",
        "Methodology": "<p>Cite [CITE_a1] here.</p>",
    })
    assert collect_used_article_ids_in_order(sections) == ["a1"]


def test_collect_dedupes_repeated_citations():
    sections = _sections({
        "Introduction": "<p>[CITE_a1] [CITE_a2] [CITE_a1]</p>",
    })
    assert collect_used_article_ids_in_order(sections) == ["a1", "a2"]


def test_collect_orders_by_canonical_section_then_first_occurrence():
    # a3 cited in Methodology, a1 in Introduction; Introduction is processed
    # first so a1 must appear before a3.
    sections = _sections({
        "Methodology": "<p>[CITE_a3]</p>",
        "Introduction": "<p>[CITE_a1]</p>",
    })
    assert collect_used_article_ids_in_order(sections) == ["a1", "a3"]


def test_collect_handles_html_sup_form():
    sections = _sections({
        "Introduction": (
            '<p>foo '
            '<sup data-citation data-article-id="a1">[1]</sup> bar '
            '<sup data-citation data-article-id="a2">[2]</sup></p>'
        ),
    })
    assert collect_used_article_ids_in_order(sections) == ["a1", "a2"]


def test_collect_handles_both_token_forms_interleaved():
    sections = _sections({
        "Introduction": (
            'foo [CITE_a1] '
            '<sup data-citation data-article-id="a2">[2]</sup> '
            '[CITE_a1] '
            '<sup data-article-id="a3" data-citation>[3]</sup>'
        ),
    })
    assert collect_used_article_ids_in_order(sections) == ["a1", "a2", "a3"]


def test_collect_canonical_section_order():
    sections = _sections({
        "Conclusion": "[CITE_c]",
        "Discussion": "[CITE_d]",
        "Results": "[CITE_r]",
        "Methodology": "[CITE_m]",
        "Introduction": "[CITE_i]",
        "Abstract": "[CITE_a]",
    })
    assert collect_used_article_ids_in_order(sections) == ["a", "i", "m", "r", "d", "c"]


def test_collect_ignores_unknown_sections():
    sections = _sections({"BogusSection": "[CITE_a1]"})
    assert collect_used_article_ids_in_order(sections) == []


def test_build_bibliography_empty_manuscript():
    assert build_bibliography(articles_by_id={}, sections=[], style="vancouver") == []


def test_build_bibliography_numbers_consecutively():
    a1 = A(title="One", authors=["John Doe"], year=2024, journal="J")
    a2 = A(title="Two", authors=["Jane Smith"], year=2023, journal="K")
    sections = _sections({"Introduction": "[CITE_a1] [CITE_a2]"})
    out = build_bibliography(
        articles_by_id={"a1": a1, "a2": a2},
        sections=sections,
        style="vancouver",
    )
    assert [e.number for e in out] == [1, 2]
    assert [e.article_id for e in out] == ["a1", "a2"]
    assert out[0].formatted.startswith("1. ")
    assert out[1].formatted.startswith("2. ")


def test_build_bibliography_drops_unknown_article_ids():
    a1 = A(title="One", authors=["John Doe"], year=2024, journal="J")
    sections = _sections({"Introduction": "[CITE_a1] [CITE_x99]"})
    out = build_bibliography(
        articles_by_id={"a1": a1},
        sections=sections,
        style="vancouver",
    )
    assert [e.article_id for e in out] == ["a1"]
    assert out[0].number == 1


@pytest.mark.parametrize("style", ["vancouver", "apa", "harvard", "ieee"])
def test_build_bibliography_respects_style(style):
    a1 = A(title="One", authors=["John Doe"], year=2024, journal="J Orthop", volume="1", pages="1-2")
    sections = _sections({"Introduction": "[CITE_a1]"})
    out = build_bibliography(
        articles_by_id={"a1": a1}, sections=sections, style=style,
    )
    assert len(out) == 1
    if style == "vancouver":
        assert out[0].formatted.startswith("1. Doe J")
    elif style == "apa":
        assert out[0].formatted.startswith("Doe, J. (2024).")
    elif style == "harvard":
        assert out[0].formatted.startswith("Doe, J. (2024) 'One'")
    elif style == "ieee":
        assert out[0].formatted.startswith('[1] J. Doe, "One,"')


def test_build_bibliography_dedupe_across_sections():
    a1 = A(title="One", authors=["John Doe"], year=2024, journal="J")
    a2 = A(title="Two", authors=["Jane Smith"], year=2023, journal="K")
    sections = _sections({
        "Introduction": "[CITE_a1]",
        "Methodology": "[CITE_a2] [CITE_a1]",
        "Discussion": "[CITE_a2]",
    })
    out = build_bibliography(
        articles_by_id={"a1": a1, "a2": a2},
        sections=sections,
        style="vancouver",
    )
    assert [e.article_id for e in out] == ["a1", "a2"]
    assert [e.number for e in out] == [1, 2]


def test_bibliography_entry_dataclass_is_frozen():
    e = BibliographyEntry(article_id="a1", number=1, formatted="X")
    with pytest.raises(Exception):
        e.number = 2  # type: ignore[misc]
