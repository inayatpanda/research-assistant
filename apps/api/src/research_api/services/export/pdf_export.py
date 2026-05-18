"""PDF manuscript export via reportlab.platypus.

Layout mirrors the DOCX export but with native SVG embedding (no rasterisation
needed — reportlab's svglib path handles `<img data:image/svg+xml>` directly).
"""
from __future__ import annotations

import base64
import io
from typing import Iterable, Protocol

from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from svglib.svglib import svg2rlg

from ._html_walker import walk_html
from .bibliography import CANONICAL_SECTION_ORDER, BibliographyEntry
from .docx_export import FrontMatterPayload, _to_superscript


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


def _make_styles() -> dict:
    base = getSampleStyleSheet()
    styles: dict = {
        "title": ParagraphStyle(
            "ManuscriptTitle", parent=base["Title"], alignment=TA_CENTER,
            fontSize=22, spaceAfter=14,
        ),
        "subtitle": ParagraphStyle(
            "ManuscriptSubtitle", parent=base["BodyText"], alignment=TA_CENTER,
            fontSize=12, textColor=colors.grey, spaceAfter=8,
        ),
        "h1": ParagraphStyle(
            "SectionH1", parent=base["Heading1"], fontSize=16, spaceBefore=14,
            spaceAfter=8,
        ),
        "h2": ParagraphStyle(
            "SectionH2", parent=base["Heading2"], fontSize=14, spaceBefore=10,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "Body", parent=base["BodyText"], fontSize=11, leading=15,
            spaceAfter=6,
        ),
        "bib": ParagraphStyle(
            "Bibliography", parent=base["BodyText"], fontSize=11, leading=14,
            leftIndent=0.5 * inch, firstLineIndent=-0.5 * inch, spaceAfter=4,
        ),
        "empty": ParagraphStyle(
            "Empty", parent=base["BodyText"], fontSize=11, textColor=colors.grey,
            spaceAfter=6,
        ),
    }
    return styles


def _order_sections(sections: Iterable[_SectionLike]) -> list[_SectionLike]:
    by_name = {s.section_name: s for s in sections}
    return [by_name[n] for n in CANONICAL_SECTION_ORDER if n in by_name]


def _decode_svg_data_uri(uri: str) -> Drawing | None:
    try:
        prefix, _, payload = uri.partition(",")
        if "base64" in prefix:
            svg_bytes = base64.b64decode(payload)
        else:
            svg_bytes = payload.encode()
        drawing = svg2rlg(io.BytesIO(svg_bytes))
        return drawing
    except Exception:
        return None


def _fit_drawing(drawing: Drawing, max_width: float) -> Drawing:
    if not drawing or drawing.width <= 0:
        return drawing
    if drawing.width > max_width:
        scale = max_width / drawing.width
        drawing.width *= scale
        drawing.height *= scale
        drawing.scale(scale, scale)
    return drawing


def _run_to_html(text: str, styles: set[str]) -> str:
    # Use reportlab's mini-HTML to render inline styles inside a Paragraph.
    from html import escape
    out = escape(text)
    if "bold" in styles:
        out = f"<b>{out}</b>"
    if "italic" in styles:
        out = f"<i>{out}</i>"
    if "underline" in styles:
        out = f"<u>{out}</u>"
    if "sup" in styles:
        out = f"<super>{out}</super>"
    return out


def _events_to_flowables(events: list[tuple], styles: dict, max_width: float) -> list:
    """Convert the HTML walker's event stream into a list of platypus flowables."""
    out: list = []
    buf_parts: list[str] = []
    in_paragraph = False
    in_table = False
    table_rows: list[list[str]] = []
    current_row: list[str] = []
    cell_parts: list[str] = []
    in_cell = False
    cell_is_header = False
    header_flags: list[list[bool]] = []
    current_header_flags: list[bool] = []

    def flush_paragraph(style_key: str = "body") -> None:
        nonlocal buf_parts, in_paragraph
        text = "".join(buf_parts).strip()
        if text:
            out.append(Paragraph(text, styles[style_key]))
        buf_parts = []
        in_paragraph = False

    for ev in events:
        kind = ev[0]
        if kind == "paragraph_start":
            in_paragraph = True
        elif kind == "paragraph_end":
            flush_paragraph()
        elif kind == "heading_start":
            flush_paragraph()
            in_paragraph = True
            # Heading text will follow as "text" events; flush on heading_end into h2.
        elif kind == "heading_end":
            flush_paragraph("h2")
        elif kind == "text":
            _, text, st = ev
            html_run = _run_to_html(text, st)
            if in_cell:
                cell_parts.append(html_run)
            elif in_paragraph or in_table:
                buf_parts.append(html_run)
            else:
                # Bare text outside any container — open a body paragraph.
                buf_parts.append(html_run)
                in_paragraph = True
        elif kind == "svg_img":
            flush_paragraph()
            drawing = _decode_svg_data_uri(ev[1])
            if drawing is not None:
                out.append(_fit_drawing(drawing, max_width))
                out.append(Spacer(1, 6))
        elif kind == "table_start":
            flush_paragraph()
            in_table = True
            table_rows = []
            header_flags = []
        elif kind == "row_start":
            current_row = []
            current_header_flags = []
        elif kind == "row_end":
            table_rows.append(current_row)
            header_flags.append(current_header_flags)
            current_row = []
            current_header_flags = []
        elif kind == "cell_start":
            in_cell = True
            cell_is_header = ev[1]
            cell_parts = []
        elif kind == "cell_end":
            cell_text = "".join(cell_parts).strip()
            current_row.append(Paragraph(cell_text, styles["body"]))
            current_header_flags.append(cell_is_header)
            in_cell = False
        elif kind == "table_end":
            if table_rows:
                t = Table(table_rows, hAlign="LEFT")
                ts = TableStyle([
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey)
                    if header_flags and any(header_flags[0]) else
                    ("BACKGROUND", (0, 0), (-1, 0), colors.white),
                ])
                t.setStyle(ts)
                out.append(t)
                out.append(Spacer(1, 6))
            in_table = False
            table_rows = []

    # Final flush.
    if buf_parts:
        flush_paragraph()
    return out


def _section_flowables(section: _SectionLike, styles: dict, max_width: float) -> list:
    out: list = [Paragraph(section.section_name, styles["h1"])]
    events = walk_html(section.content or "")
    body = _events_to_flowables(events, styles, max_width) if events else []
    if not body:
        out.append(Paragraph("(Empty)", styles["empty"]))
    else:
        out.extend(body)
    out.append(Spacer(1, 12))
    return out


def _frontmatter_flowables(
    fm: FrontMatterPayload, styles: dict
) -> list:
    """Title page authors + affiliations + corresponding-author line.

    Mirrors `docx_export._add_authors_block` but emits reportlab flowables.
    All user text is `html.escape`d before mini-HTML composition.
    """
    from html import escape

    out: list = []
    aff_by_id = {a["id"]: a for a in fm.affiliations}
    seen: dict[str, int] = {}
    ordered_affs: list[dict] = []
    for author in sorted(fm.authors, key=lambda a: a.get("position", 0)):
        for aff_id in author.get("affiliation_ids") or []:
            if aff_id in seen or aff_id not in aff_by_id:
                continue
            seen[aff_id] = len(seen) + 1
            ordered_affs.append(aff_by_id[aff_id])

    chunks: list[str] = []
    for author in sorted(fm.authors, key=lambda a: a.get("position", 0)):
        name = escape(author.get("full_name") or "")
        nums = [
            seen[aid]
            for aid in (author.get("affiliation_ids") or [])
            if aid in seen
        ]
        sup = "".join(_to_superscript(n) for n in sorted(nums))
        star = "*" if author.get("is_corresponding") else ""
        chunks.append(f"{name}{sup}{star}")
    if chunks:
        out.append(Paragraph(", ".join(chunks), styles["subtitle"]))
    for aff in ordered_affs:
        number = seen[aff["id"]]
        parts = [escape(aff.get(k) or "") for k in ("name", "address", "city", "country")]
        text = ", ".join(p for p in parts if p)
        out.append(
            Paragraph(
                f"{_to_superscript(number)} <i>{text}</i>", styles["subtitle"]
            )
        )
    corresponding = next(
        (a for a in fm.authors if a.get("is_corresponding")), None
    )
    if corresponding and corresponding.get("email"):
        out.append(
            Paragraph(
                f"<b>* Corresponding author:</b> {escape(corresponding['email'])}",
                styles["subtitle"],
            )
        )
    return out


def _structured_abstract_flowables(abstract: dict, styles: dict) -> list:
    from html import escape

    out: list = [Paragraph("Abstract", styles["h1"])]
    for label, key in [
        ("Background", "background"),
        ("Methods", "methods"),
        ("Results", "results"),
        ("Conclusions", "conclusions"),
    ]:
        text = escape(abstract.get(key, "") or "") or "(Empty)"
        out.append(Paragraph(f"<b>{label}:</b> {text}", styles["body"]))
    return out


def _frontmatter_statements(fm: FrontMatterPayload, styles: dict) -> list:
    from html import escape

    out: list = []

    def emit(label: str, body: str | None) -> None:
        if not body:
            return
        out.append(Paragraph(f"<b>{label}</b>", styles["body"]))
        out.append(Paragraph(escape(body), styles["body"]))

    emit("Conflicts of Interest", fm.conflicts_statement)
    # Funding (statement + structured funder list)
    funding_parts: list[str] = []
    if fm.funding_statement:
        funding_parts.append(fm.funding_statement.strip())
    if fm.funders:
        chunks = []
        for f in fm.funders:
            name = (f.get("name") or "").strip()
            grant = (f.get("grant_id") or "").strip()
            if not name:
                continue
            chunks.append(f"{name} ({grant})" if grant else name)
        if chunks:
            funding_parts.append("Funders: " + "; ".join(chunks) + ".")
    emit("Funding", " ".join(funding_parts) or None)
    # Ethics
    ethics_parts: list[str] = []
    if fm.ethics_irb:
        ethics_parts.append(f"IRB: {fm.ethics_irb.strip()}.")
    if fm.ethics_approval_number:
        ethics_parts.append(f"Approval number: {fm.ethics_approval_number.strip()}.")
    if fm.ethics_consent:
        ethics_parts.append(fm.ethics_consent.strip())
    emit("Ethics", " ".join(ethics_parts) or None)
    return out


def render_pdf(
    *,
    project: _ProjectLike,
    sections: Iterable[_SectionLike],
    bibliography: list[BibliographyEntry],
    frontmatter: FrontMatterPayload | None = None,
) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=1 * inch, rightMargin=1 * inch,
        topMargin=1 * inch, bottomMargin=1 * inch,
        title=project.title or "Manuscript",
    )
    styles = _make_styles()
    max_width = doc.width
    story: list = [Paragraph(project.title or "Untitled", styles["title"])]
    if frontmatter and frontmatter.authors:
        story.extend(_frontmatter_flowables(frontmatter, styles))
    else:
        story.append(
            Paragraph(f"Study type: {project.study_type}", styles["subtitle"])
        )
        story.append(
            Paragraph(
                f"Citation style: {_style_label(project.citation_style)}",
                styles["subtitle"],
            )
        )
    story.append(Spacer(1, 24))

    use_structured = bool(
        frontmatter
        and frontmatter.structured_abstract_enabled
        and frontmatter.structured_abstract
    )
    for section in _order_sections(sections):
        if use_structured and section.section_name == "Abstract":
            story.extend(
                _structured_abstract_flowables(
                    frontmatter.structured_abstract, styles  # type: ignore[union-attr]
                )
            )
            story.append(Spacer(1, 12))
        else:
            story.extend(_section_flowables(section, styles, max_width))
    if bibliography:
        story.append(Paragraph("References", styles["h1"]))
        for entry in bibliography:
            story.append(Paragraph(f"{entry.number}. {entry.formatted}", styles["bib"]))
    if frontmatter:
        story.extend(_frontmatter_statements(frontmatter, styles))
    doc.build(story)
    return buf.getvalue()
