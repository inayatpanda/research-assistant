"""Phase 4.5 — Pure-function tests for the articles-table HTML builder."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from research_api.schemas.articles_table import ColumnSpec
from research_api.services.manuscript.articles_table import (
    build_articles_table_html,
    render_author_year,
)


@dataclass
class _Article:
    id: str
    title: str | None = None
    authors: list[str] = field(default_factory=list)
    journal: str | None = None
    year: int | None = None
    doi: str | None = None
    url: str | None = None
    study_design: str | None = None


@dataclass
class _Extraction:
    article_id: str
    fields: dict[str, Any] = field(default_factory=dict)


# ── render_author_year ──────────────────────────────────────────────────


def test_author_year_single_author():
    art = _Article(id="a1", authors=["Smith J"], year=2024)
    assert render_author_year(art) == "Smith (2024)"


def test_author_year_two_authors_uses_and():
    art = _Article(id="a1", authors=["Smith J", "Jones K"], year=2023)
    assert render_author_year(art) == "Smith and Jones (2023)"


def test_author_year_three_authors_uses_et_al():
    art = _Article(
        id="a1",
        authors=["Smith J", "Jones K", "Doe A"],
        year=2022,
    )
    assert render_author_year(art) == "Smith et al. (2022)"


def test_author_year_full_list_when_et_al_disabled():
    art = _Article(
        id="a1",
        authors=["Smith J", "Jones K", "Doe A"],
        year=2022,
    )
    out = render_author_year(art, include_et_al=False)
    assert out == "Smith, Jones, Doe (2022)"


def test_author_year_full_authors_flag_forces_list():
    art = _Article(
        id="a1",
        authors=["Smith J", "Jones K"],
        year=2020,
    )
    out = render_author_year(art, include_full_authors=True)
    assert out == "Smith, Jones (2020)"


def test_author_year_handles_first_last_order():
    art = _Article(id="a1", authors=["John Smith"], year=2024)
    assert render_author_year(art) == "Smith (2024)"


def test_author_year_no_authors_uses_anonymous():
    art = _Article(id="a1", authors=[], year=2024)
    assert render_author_year(art) == "Anonymous (2024)"


def test_author_year_handles_missing_year():
    art = _Article(id="a1", authors=["Smith J"], year=None)
    assert render_author_year(art) == "Smith (n.d.)"


# ── build_articles_table_html ───────────────────────────────────────────


def _three_articles() -> list[_Article]:
    return [
        _Article(
            id="a1",
            title="Effect of X on Y",
            authors=["Smith J"],
            journal="Lancet",
            year=2024,
            doi="10.1/x",
            study_design="rct",
        ),
        _Article(
            id="a2",
            title="A cohort study",
            authors=["Doe A", "Roe B"],
            journal="JAMA",
            year=2023,
            study_design="cohort",
        ),
        _Article(
            id="a3",
            title="Multi-author analysis",
            authors=["Adams C", "Brown D", "Cole E", "Davis F"],
            journal="NEJM",
            year=2022,
            study_design="rct",
        ),
    ]


def test_build_table_renders_three_rows_with_correct_author_cells():
    arts = _three_articles()
    cols = [
        ColumnSpec(preset="author_year_citation", label="Study"),
        ColumnSpec(preset="title", label="Title"),
    ]
    html = build_articles_table_html(arts, {}, cols)
    assert "<table" in html and "rma-articles-table" in html
    # The Citation NodeView markup is always emitted
    assert 'data-citation="true"' in html
    assert 'data-article-id="a1"' in html
    assert "Smith (2024)" in html
    assert "Doe and Roe (2023)" in html
    assert "Adams et al. (2022)" in html
    # Titles are escaped + present
    assert "Effect of X on Y" in html


def test_build_table_first_column_synthesised_if_missing():
    """Defence in depth — the dialog enforces this on the FE side too."""
    arts = _three_articles()
    cols = [ColumnSpec(preset="title", label="Title")]
    html = build_articles_table_html(arts, {}, cols)
    # Author-year column should still be present in the header & body
    assert "Smith (2024)" in html
    assert 'data-article-id="a1"' in html


def test_build_table_custom_column_renders_empty_cells():
    arts = _three_articles()[:1]
    cols = [
        ColumnSpec(preset="author_year_citation", label="Study"),
        ColumnSpec(preset=None, label="My notes"),
    ]
    html = build_articles_table_html(arts, {}, cols)
    assert ">My notes<" in html
    # Custom cell renders as <td><p></p></td>
    assert "<td><p></p></td>" in html


def test_build_table_extraction_columns_fill_when_record_present():
    arts = _three_articles()[:1]
    ext = _Extraction(
        article_id="a1",
        fields={
            "basic": {"country": "UK"},
            "population": {"n_total": 320},
            "intervention": {"name": "TKA"},
            "comparator": {"name": "Conservative"},
            "outcomes": {"outcomes": [{"name": "Pain at 6 months"}]},
        },
    )
    cols = [
        ColumnSpec(preset="author_year_citation", label="Study"),
        ColumnSpec(preset="country", label="Country"),
        ColumnSpec(preset="sample_size_n", label="N"),
        ColumnSpec(preset="intervention", label="Intervention"),
        ColumnSpec(preset="comparator", label="Comparator"),
        ColumnSpec(preset="primary_outcome", label="Outcome"),
    ]
    html = build_articles_table_html(arts, {"a1": ext}, cols)
    assert "<td><p>UK</p></td>" in html
    assert "<td><p>320</p></td>" in html
    assert "<td><p>TKA</p></td>" in html
    assert "<td><p>Conservative</p></td>" in html
    assert "Pain at 6 months" in html


def test_build_table_extraction_missing_renders_empty():
    arts = _three_articles()
    cols = [
        ColumnSpec(preset="author_year_citation", label="Study"),
        ColumnSpec(preset="country", label="Country"),
        ColumnSpec(preset="sample_size_n", label="N"),
    ]
    html = build_articles_table_html(arts, {}, cols)
    # No extraction provided — country/N cells must be empty (no exceptions)
    assert ">UK<" not in html
    # All three rows present with empty extraction cells
    assert html.count("<tr>") == 4  # 1 header tr + 3 body rows


def test_build_table_inline_mode_doesnt_break_sup_markup():
    """All three inline modes must still emit the <sup data-citation> markup
    — the NodeView on the FE handles the visible difference (e.g. removing
    the brackets for author-year). This guarantees the bibliography
    counts the citation regardless of how the user displays it."""
    arts = _three_articles()[:1]
    cols = [ColumnSpec(preset="author_year_citation", label="Study")]
    for mode in ("bracket_numeric", "superscript_numeric", "author_year_parens"):
        html = build_articles_table_html(
            arts, {}, cols, inline_citation_mode=mode  # type: ignore[arg-type]
        )
        assert 'data-citation="true"' in html
        assert 'data-article-id="a1"' in html


def test_build_table_escapes_unsafe_strings():
    arts = [
        _Article(
            id="a1",
            title="<script>x</script>",
            authors=["Smith J"],
            journal="J & A",
            year=2024,
        ),
    ]
    cols = [
        ColumnSpec(preset="author_year_citation", label="Study"),
        ColumnSpec(preset="title", label="Title"),
        ColumnSpec(preset="journal", label="Journal"),
    ]
    html = build_articles_table_html(arts, {}, cols)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "J &amp; A" in html


def test_build_table_study_design_falls_back_to_extraction():
    """When ``article.study_design`` is empty, fall back to extraction
    ``basic.design`` (older data shape)."""
    arts = [_Article(id="a1", authors=["Smith J"], year=2024)]
    ext = _Extraction(article_id="a1", fields={"basic": {"design": "RCT"}})
    cols = [
        ColumnSpec(preset="author_year_citation", label="Study"),
        ColumnSpec(preset="study_design", label="Design"),
    ]
    html = build_articles_table_html(arts, {"a1": ext}, cols)
    assert "<td><p>RCT</p></td>" in html


def test_build_table_year_zero_renders_empty():
    # year=None should produce an empty cell, not "None"
    arts = [_Article(id="a1", authors=["Smith J"], year=None)]
    cols = [
        ColumnSpec(preset="author_year_citation", label="Study"),
        ColumnSpec(preset="year", label="Year"),
    ]
    html = build_articles_table_html(arts, {}, cols)
    # year cell must be empty
    assert "<td><p></p></td>" in html
