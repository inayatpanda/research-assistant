"""PDF export — TDD via pypdf to extract the produced text.

Layout mirrors DOCX:
  - title page,
  - section headings in canonical order,
  - prose paragraphs,
  - tables,
  - embedded SVG (PRISMA) rendered natively via svglib/reportlab,
  - bibliography with hanging-indent paragraphs.
"""
from __future__ import annotations

import io
from dataclasses import dataclass, field
from datetime import datetime, timezone

from pypdf import PdfReader

from research_api.db.models import Project
from research_api.services.export.bibliography import BibliographyEntry
from research_api.services.export.pdf_export import render_pdf


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


def _project(citation_style: str = "vancouver", title: str = "Test Project") -> Project:
    p = Project(
        id="proj1", user_id="user-a", title=title,
        study_type="Outcome Study", citation_style=citation_style,
        ai_provider="gemini",
    )
    p.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    p.updated_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return p


def _pdf_text(blob: bytes) -> str:
    reader = PdfReader(io.BytesIO(blob))
    return "\n".join(p.extract_text() for p in reader.pages)


def test_render_pdf_returns_pdf_bytes():
    blob = render_pdf(project=_project(), sections=[], bibliography=[])
    assert isinstance(blob, bytes)
    assert blob.startswith(b"%PDF-")


def test_render_pdf_contains_title():
    blob = render_pdf(project=_project(), sections=[], bibliography=[])
    text = _pdf_text(blob)
    assert "Test Project" in text
    assert "Outcome Study" in text


def test_render_pdf_renders_sections_in_canonical_order():
    sections = [
        Section("Conclusion", "<p>Wrap.</p>"),
        Section("Introduction", "<p>Intro text.</p>"),
        Section("Results", "<p>Results text.</p>"),
    ]
    blob = render_pdf(project=_project(), sections=sections, bibliography=[])
    text = _pdf_text(blob)
    intro = text.find("Introduction")
    res = text.find("Results")
    conc = text.find("Conclusion")
    assert intro != -1
    assert res != -1
    assert conc != -1
    assert intro < res < conc


def test_render_pdf_empty_section_shows_placeholder():
    sections = [Section("Introduction", "")]
    blob = render_pdf(project=_project(), sections=sections, bibliography=[])
    text = _pdf_text(blob)
    assert "Introduction" in text
    assert "(Empty)" in text


def test_render_pdf_renders_bibliography_entries():
    bib = [
        BibliographyEntry(article_id="a1", number=1, formatted="Doe J. A study. JAMA. 2024;1:1-2."),
        BibliographyEntry(article_id="a2", number=2, formatted="Smith K. Other. NEJM. 2023;2:3-4."),
    ]
    blob = render_pdf(project=_project(), sections=[], bibliography=bib)
    text = _pdf_text(blob)
    assert "References" in text
    assert "Doe J" in text
    assert "Smith K" in text


def test_render_pdf_strips_script_tags():
    sections = [Section("Introduction", "<p>safe</p><script>alert('xss')</script>")]
    blob = render_pdf(project=_project(), sections=sections, bibliography=[])
    text = _pdf_text(blob)
    assert "alert" not in text
    assert "safe" in text


def test_render_pdf_renders_table_from_html():
    html = (
        "<table>"
        "<tr><th>Study</th><th>RoB</th></tr>"
        "<tr><td>Smith 2020</td><td>Low</td></tr>"
        "<tr><td>Jones 2021</td><td>High</td></tr>"
        "</table>"
    )
    sections = [Section("Results", html)]
    blob = render_pdf(project=_project(), sections=sections, bibliography=[])
    text = _pdf_text(blob)
    assert "Smith 2020" in text
    assert "Jones 2021" in text


def test_render_pdf_handles_inline_citation_sup():
    sections = [Section(
        "Introduction",
        '<p>Foo <sup data-citation data-article-id="a1">[1]</sup> bar.</p>',
    )]
    bib = [BibliographyEntry(article_id="a1", number=1, formatted="Doe J. ...")]
    blob = render_pdf(project=_project(citation_style="ieee"),
                      sections=sections, bibliography=bib)
    text = _pdf_text(blob)
    assert "Foo" in text
    assert "bar" in text


def test_render_pdf_embeds_svg_without_crash():
    # Minimal SVG via data-URI. The PDF backend should embed it (svglib).
    svg = '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100"><rect width="200" height="100" fill="red"/></svg>'
    import base64
    b64 = base64.b64encode(svg.encode()).decode()
    sections = [Section("Methodology", f'<p>Flow:</p><img src="data:image/svg+xml;base64,{b64}"/>')]
    blob = render_pdf(project=_project(), sections=sections, bibliography=[])
    assert blob.startswith(b"%PDF-")
    # The pages list must have at least one page; the SVG embeds successfully.
    reader = PdfReader(io.BytesIO(blob))
    assert len(reader.pages) >= 1


def test_render_pdf_page_count_grows_with_content():
    short = render_pdf(project=_project(), sections=[], bibliography=[])
    long_content = "<p>" + (" ".join(["word"] * 1000)) + "</p>"
    sections = [Section("Introduction", long_content)]
    long_pdf = render_pdf(project=_project(), sections=sections, bibliography=[])
    short_pages = len(PdfReader(io.BytesIO(short)).pages)
    long_pages = len(PdfReader(io.BytesIO(long_pdf)).pages)
    assert long_pages > short_pages
