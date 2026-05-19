"""Phase 13.5 (MP13.5) — Statistical report PDF builder.

Walks all analyses on a dataset + their charts + assumption checks + AI
interpretations -> multi-page PDF via reportlab.platypus. Plot rows from the
dataset_plots table are appended after the analyses section.

Pure function: takes typed payloads, returns bytes. No DB / FS calls.
"""
from __future__ import annotations

import base64
import io
from dataclasses import dataclass
from datetime import datetime
from html import escape
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


@dataclass(frozen=True)
class ReportProject:
    title: str
    study_type: str


@dataclass(frozen=True)
class ReportDataset:
    id: str
    filename: str
    n_rows: int
    n_columns: int


@dataclass(frozen=True)
class ReportTransformation:
    op_type: str
    label: str
    op_args: dict[str, Any]


@dataclass(frozen=True)
class ReportAnalysis:
    test_label: str
    variables: dict[str, Any]
    summary: dict[str, Any]
    assumptions: dict[str, Any]
    chart_data_uri: str | None
    ai_interpretation: str | None


@dataclass(frozen=True)
class ReportPlot:
    title: str
    geom: str
    png_data_uri: str


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "T", parent=base["Title"], alignment=TA_CENTER, fontSize=22, spaceAfter=14
        ),
        "subtitle": ParagraphStyle(
            "ST", parent=base["BodyText"], alignment=TA_CENTER, fontSize=12,
            textColor=colors.grey, spaceAfter=8,
        ),
        "h1": ParagraphStyle(
            "H1", parent=base["Heading1"], fontSize=15, spaceBefore=14, spaceAfter=8
        ),
        "h2": ParagraphStyle(
            "H2", parent=base["Heading2"], fontSize=12, spaceBefore=8, spaceAfter=4
        ),
        "body": ParagraphStyle(
            "B", parent=base["BodyText"], fontSize=10, leading=14,
            alignment=TA_LEFT, spaceAfter=4,
        ),
        "small": ParagraphStyle(
            "S", parent=base["BodyText"], fontSize=9, leading=12,
            textColor=colors.grey,
        ),
        "mono": ParagraphStyle(
            "M", parent=base["Code"], fontSize=9, leading=12,
        ),
    }


def _decode_data_uri(uri: str) -> bytes | None:
    if not uri:
        return None
    try:
        prefix, _, payload = uri.partition(",")
        if "base64" not in prefix:
            return None
        return base64.b64decode(payload)
    except Exception:
        return None


def _image_flowable(uri: str, max_width: float, max_height: float = 4.0 * inch) -> Image | None:
    raw = _decode_data_uri(uri)
    if raw is None:
        return None
    try:
        img = Image(io.BytesIO(raw))
    except Exception:
        return None
    # Scale to fit
    iw = float(getattr(img, "imageWidth", 0) or 1)
    ih = float(getattr(img, "imageHeight", 0) or 1)
    aspect = ih / iw if iw else 1.0
    w = min(max_width, iw)
    h = w * aspect
    if h > max_height:
        h = max_height
        w = h / aspect if aspect else max_width
    img.drawWidth = w
    img.drawHeight = h
    return img


def _fmt(v: Any) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        if v != v:  # NaN
            return "—"
        if abs(v) < 1e-3 or abs(v) >= 1e6:
            return f"{v:.3e}"
        return f"{v:.4f}"
    return str(v)


def _summary_table(summary: dict[str, Any], styles: dict) -> Table:
    rows = [
        ["Statistic", _fmt(summary.get("statistic"))],
        ["p-value", _fmt(summary.get("p_value"))],
        ["Effect size", _fmt(summary.get("effect_size"))],
        ["95% CI low", _fmt(summary.get("ci_low"))],
        ["95% CI high", _fmt(summary.get("ci_high"))],
        ["n", _fmt(summary.get("n"))],
        ["df", _fmt(summary.get("df"))],
    ]
    cells = [
        [Paragraph(label, styles["body"]), Paragraph(val, styles["body"])]
        for label, val in rows
    ]
    t = Table(cells, hAlign="LEFT", colWidths=[1.5 * inch, 1.8 * inch])
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return t


def _assumptions_lines(assumptions: dict[str, Any], styles: dict) -> list[Any]:
    out: list[Any] = []
    if not assumptions:
        return out
    out.append(Paragraph("<b>Assumptions</b>", styles["h2"]))
    for name, payload in assumptions.items():
        if not isinstance(payload, dict):
            continue
        ok = payload.get("ok")
        verdict = "pass" if ok else ("fail" if ok is False else "—")
        p = payload.get("p_value")
        stat = payload.get("statistic")
        line = f"{escape(name)}: <b>{verdict}</b> (stat={_fmt(stat)}, p={_fmt(p)})"
        out.append(Paragraph(line, styles["body"]))
    return out


def build_stats_report(
    *,
    project: ReportProject,
    dataset: ReportDataset,
    analyses: list[ReportAnalysis],
    plots: list[ReportPlot],
    transformations: list[ReportTransformation],
) -> bytes:
    """Render the full statistical report PDF to bytes."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=0.9 * inch,
        rightMargin=0.9 * inch,
        topMargin=0.9 * inch,
        bottomMargin=0.9 * inch,
        title=f"{project.title} — statistical report",
    )
    max_width = doc.width
    styles = _styles()
    story: list = []

    # ── Title page ───────────────────────────────────────────────────
    story.append(Paragraph(escape(project.title or "Untitled project"), styles["title"]))
    story.append(Paragraph(escape(project.study_type or ""), styles["subtitle"]))
    story.append(Paragraph(
        f"Statistical report — generated {datetime.utcnow().strftime('%Y-%m-%d')}",
        styles["subtitle"],
    ))
    story.append(Spacer(1, 14))
    story.append(Paragraph("Dataset", styles["h1"]))
    story.append(Paragraph(
        f"<b>Filename:</b> {escape(dataset.filename)}", styles["body"]
    ))
    story.append(Paragraph(
        f"<b>Rows:</b> {dataset.n_rows} &nbsp; <b>Columns:</b> {dataset.n_columns}",
        styles["body"],
    ))
    story.append(Paragraph(
        f"<b>Dataset ID:</b> {escape(dataset.id)}", styles["small"]
    ))

    if transformations:
        story.append(Paragraph("Transformation stack", styles["h1"]))
        for i, t in enumerate(transformations, start=1):
            label = t.label or t.op_type
            story.append(Paragraph(
                f"{i}. <b>{escape(t.op_type)}</b> — {escape(label)}",
                styles["body"],
            ))

    # ── Analyses ─────────────────────────────────────────────────────
    if analyses:
        story.append(PageBreak())
        story.append(Paragraph("Analyses", styles["h1"]))
        for idx, a in enumerate(analyses, start=1):
            story.append(Paragraph(
                f"Analysis {idx} — {escape(a.test_label)}", styles["h2"]
            ))
            var_lines = ", ".join(
                f"<i>{escape(k)}</i>: {escape(str(v))}"
                for k, v in (a.variables or {}).items()
            )
            if var_lines:
                story.append(Paragraph(
                    f"<b>Variables:</b> {var_lines}", styles["body"]
                ))
            story.append(_summary_table(a.summary or {}, styles))
            story.extend(_assumptions_lines(a.assumptions or {}, styles))
            if a.chart_data_uri:
                img = _image_flowable(a.chart_data_uri, max_width)
                if img is not None:
                    story.append(Spacer(1, 6))
                    story.append(img)
            if a.ai_interpretation:
                story.append(Paragraph("<b>Interpretation</b>", styles["h2"]))
                story.append(Paragraph(escape(a.ai_interpretation), styles["body"]))
            story.append(Spacer(1, 12))

    # ── Plots ────────────────────────────────────────────────────────
    if plots:
        story.append(PageBreak())
        story.append(Paragraph("Plots", styles["h1"]))
        for idx, p in enumerate(plots, start=1):
            label = p.title or f"{p.geom.capitalize()} plot"
            story.append(Paragraph(f"{idx}. {escape(label)}", styles["h2"]))
            img = _image_flowable(p.png_data_uri, max_width)
            if img is not None:
                story.append(img)
            story.append(Spacer(1, 10))

    # ── References / dataset citation ────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("References", styles["h1"]))
    story.append(Paragraph(
        f"Dataset: {escape(dataset.filename)} (id={escape(dataset.id)}).",
        styles["body"],
    ))

    doc.build(story)
    return buf.getvalue()
