"""DOCX manuscript export via python-docx.

Layout:
  - title page (project title as H1; study type + citation style).
  - one heading per section in canonical order (Abstract → Conclusion).
  - prose paragraphs (HTML parsed via `_html_walker`).
  - tables from `<table>` blocks.
  - References section at the end with hanging-indent paragraphs.

PRISMA `<img data:image/svg+xml>` images are replaced with a placeholder
caption paragraph — the DOCX export skips raster conversion because the dev
machine ships without cairo. The PDF export embeds the same SVGs natively.
"""
from __future__ import annotations

import io
from typing import Iterable, Protocol

from docx import Document
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.shared import Inches, Pt

from ._html_walker import walk_html
from .bibliography import CANONICAL_SECTION_ORDER, BibliographyEntry

PRISMA_PLACEHOLDER = (
    "Figure: PRISMA 2020 flow diagram (rendered in the online manuscript)."
)


class _ProjectLike(Protocol):
    title: str
    study_type: str
    citation_style: str


class _SectionLike(Protocol):
    section_name: str
    content: str


def _style_label(style: str) -> str:
    return {"vancouver": "Vancouver", "apa": "APA 7th",
            "harvard": "Harvard", "ieee": "IEEE"}.get(style, style)


def _configure_page(document: Document) -> None:
    for section in document.sections:
        section.page_width = Inches(8.27)   # A4 width
        section.page_height = Inches(11.69)  # A4 height
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)
    style = document.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(11)


def _add_title_page(document: Document, project: _ProjectLike) -> None:
    title = document.add_heading(project.title, level=0)
    title.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    p = document.add_paragraph()
    p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    p.add_run(f"Study type: {project.study_type}").italic = True
    p2 = document.add_paragraph()
    p2.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    p2.add_run(f"Citation style: {_style_label(project.citation_style)}").italic = True
    document.add_paragraph()  # blank spacer


def _order_sections(sections: Iterable[_SectionLike]) -> list[_SectionLike]:
    by_name = {s.section_name: s for s in sections}
    return [by_name[n] for n in CANONICAL_SECTION_ORDER if n in by_name]


def _add_run(paragraph, text: str, styles: set[str]) -> None:
    run = paragraph.add_run(text)
    if "bold" in styles:
        run.bold = True
    if "italic" in styles:
        run.italic = True
    if "sup" in styles:
        run.font.superscript = True
    if "underline" in styles:
        run.underline = True


def _render_events(document: Document, events: list[tuple]) -> None:
    """Walk the event stream and emit DOCX paragraphs / tables."""
    paragraph = None
    table = None
    row_cells: list = []
    cell_idx = 0
    pending_cell_paragraph = None

    def flush_paragraph() -> None:
        nonlocal paragraph
        paragraph = None

    for ev in events:
        kind = ev[0]
        if kind == "paragraph_start":
            paragraph = document.add_paragraph()
        elif kind == "paragraph_end":
            flush_paragraph()
        elif kind == "heading_start":
            level = ev[1]
            paragraph = document.add_heading("", level=min(max(level, 1), 4))
        elif kind == "heading_end":
            flush_paragraph()
        elif kind == "text":
            _, text, styles = ev
            if pending_cell_paragraph is not None:
                _add_run(pending_cell_paragraph, text, styles)
            elif paragraph is not None:
                _add_run(paragraph, text, styles)
        elif kind == "svg_img":
            flush_paragraph()
            p = document.add_paragraph()
            p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
            run = p.add_run(PRISMA_PLACEHOLDER)
            run.italic = True
        elif kind == "table_start":
            flush_paragraph()
            table = document.add_table(rows=0, cols=0)
            table.style = "Table Grid"
        elif kind == "row_start":
            if table is None:
                continue
            row = table.add_row()
            row_cells = list(row.cells)
            cell_idx = 0
        elif kind == "row_end":
            row_cells = []
            cell_idx = 0
        elif kind == "cell_start":
            is_header = ev[1]
            if table is None:
                continue
            # Add a column on the fly if the row needs more cells than exist.
            while cell_idx >= len(row_cells):
                # python-docx requires explicit column add to extend the row.
                if not table.columns or cell_idx >= len(table.columns):
                    table.add_column(Inches(1.0))
                row_cells = list(table.rows[-1].cells)
            cell = row_cells[cell_idx]
            cell.text = ""  # clear default empty paragraph
            pending_cell_paragraph = cell.paragraphs[0]
            if is_header:
                for run in pending_cell_paragraph.runs:
                    run.bold = True
        elif kind == "cell_end":
            pending_cell_paragraph = None
            cell_idx += 1
        elif kind == "table_end":
            table = None


def _add_section(document: Document, section: _SectionLike) -> None:
    document.add_heading(section.section_name, level=1)
    events = walk_html(section.content or "")
    if not events:
        p = document.add_paragraph()
        p.add_run("(Empty)").italic = True
        return
    _render_events(document, events)


def _add_bibliography(document: Document, entries: list[BibliographyEntry]) -> None:
    if not entries:
        return
    document.add_page_break()
    document.add_heading("References", level=1)
    for entry in entries:
        p = document.add_paragraph()
        p.paragraph_format.left_indent = Inches(0.5)
        p.paragraph_format.first_line_indent = Inches(-0.5)
        p.add_run(f"{entry.number}. {entry.formatted}")


def render_docx(
    *,
    project: _ProjectLike,
    sections: Iterable[_SectionLike],
    bibliography: list[BibliographyEntry],
) -> bytes:
    """Return the DOCX bytes for the manuscript."""
    document = Document()
    _configure_page(document)
    _add_title_page(document, project)
    for section in _order_sections(sections):
        _add_section(document, section)
    _add_bibliography(document, bibliography)
    buf = io.BytesIO()
    document.save(buf)
    return buf.getvalue()
