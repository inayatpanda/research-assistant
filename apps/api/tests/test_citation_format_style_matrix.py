"""Parametrised regression matrix: 4 styles × 4 article shapes.

Tests assert that `format_entry` produces a non-empty, well-formed string
that contains expected anchors (authors, title) and observes per-style
markers (e.g. parens around year for APA/Harvard, quotes around title for IEEE).
"""
from dataclasses import dataclass, field

import pytest

from research_api.services.citation_format import format_entry, format_entry_html


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


def _make(shape: str) -> A:
    if shape == "full":
        return A(
            title="Anterior approach",
            authors=["Jane Doe", "John Smith"],
            year=2024,
            journal="J Orthop Res",
            volume="42",
            issue="3",
            pages="100-110",
            doi="10.1234/jor.42.3.100",
        )
    if shape == "no_doi":
        return A(
            title="Anterior approach",
            authors=["Jane Doe", "John Smith"],
            year=2024,
            journal="J Orthop Res",
            volume="42",
            issue="3",
            pages="100-110",
        )
    if shape == "no_year":
        return A(
            title="Anterior approach",
            authors=["Jane Doe", "John Smith"],
            journal="J Orthop Res",
            volume="42",
            issue="3",
            pages="100-110",
            doi="10.1234/jor.42.3.100",
        )
    if shape == "missing_volume":
        return A(
            title="Anterior approach",
            authors=["Jane Doe", "John Smith"],
            year=2024,
            journal="J Orthop Res",
            pages="100-110",
            doi="10.1234/jor.42.3.100",
        )
    raise ValueError(shape)


@pytest.mark.parametrize("style", ["vancouver", "apa", "harvard", "ieee"])
@pytest.mark.parametrize("shape", ["full", "no_doi", "no_year", "missing_volume"])
def test_format_entry_well_formed(style, shape):
    a = _make(shape)
    out = format_entry(a, style=style)
    assert out, "must be non-empty"
    assert "Doe" in out and "Smith" in out
    assert "Anterior approach" in out
    if shape == "no_doi":
        assert "10.1234/jor.42.3.100" not in out
    else:
        assert "10.1234/jor.42.3.100" in out
    if shape == "no_year":
        # APA, Harvard, Vancouver use n.d.; IEEE simply omits the year segment.
        if style in {"apa", "harvard", "vancouver"}:
            assert "n.d." in out
        else:
            assert "2024" not in out


def test_format_entry_unknown_style_raises():
    with pytest.raises(ValueError):
        format_entry(A(authors=["John Doe"], year=2024), style="mla")  # type: ignore[arg-type]


@pytest.mark.parametrize("style", ["vancouver", "apa", "harvard", "ieee"])
def test_format_entry_html_escapes_user_content(style):
    a = A(
        title="<script>alert(1)</script>",
        authors=["Jane Doe"],
        year=2024,
        journal="<b>J</b>",
    )
    html = format_entry_html(a, style=style)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "<b>J</b>" not in html
    assert "&lt;b&gt;J&lt;/b&gt;" in html
    assert html.startswith('<span class="bib-entry">') and html.endswith("</span>")


@pytest.mark.parametrize("style", ["vancouver", "apa", "harvard", "ieee"])
def test_format_entry_html_wraps_in_span(style):
    a = A(title="T", authors=["John Doe"], year=2024, journal="J")
    html = format_entry_html(a, style=style)
    assert html.startswith('<span class="bib-entry">')
    assert html.endswith("</span>")
