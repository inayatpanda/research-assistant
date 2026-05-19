"""Phase 14 (MP14) — Summary-of-Findings (SoF) HTML table renderer.

Pure function — no DB / FS / network. Given a list of GRADE assessments and
a parallel lookup of meta-analysis results (keyed by ``meta_id``), produce
a single ``<table class="sof-table">`` block ready to push into the
manuscript's Results section.

Citations: any included-article cite tokens carried in ``meta_inputs`` (one
per pooled study) are rendered as ``[CITE_<aid>]`` so the existing
``replace_cite_tokens_with_markup`` pipeline can resolve them on render.
"""
from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Any, Iterable


@dataclass(frozen=True)
class SofMetaSummary:
    """Subset of MetaAnalysis fields the SoF table consumes."""

    meta_id: str
    effect_metric: str
    n_studies: int
    pooled_estimate: float | None
    ci_low: float | None
    ci_high: float | None
    # Article ids of the pooled studies (used to render CITE tokens).
    article_ids: tuple[str, ...] = ()


_METRIC_LABELS: dict[str, str] = {
    "md": "MD",
    "smd": "SMD",
    "or": "OR",
    "rr": "RR",
    "hr": "HR",
    "r": "r",
}


_CERTAINTY_LABELS: dict[str, tuple[str, str]] = {
    "high": ("High", "⊕⊕⊕⊕"),
    "moderate": ("Moderate", "⊕⊕⊕⊖"),
    "low": ("Low", "⊕⊕⊖⊖"),
    "very_low": ("Very low", "⊕⊖⊖⊖"),
}


def _fmt_effect(metric: str, est: float | None, lo: float | None, hi: float | None) -> str:
    if est is None or lo is None or hi is None:
        return "&mdash;"
    label = _METRIC_LABELS.get(metric, metric.upper())
    return f"{label} {est:.2f} (95% CI {lo:.2f} to {hi:.2f})"


def _badge(certainty: str) -> str:
    label, symbols = _CERTAINTY_LABELS.get(
        certainty, (certainty.title(), "")
    )
    return (
        f'<span class="cert cert-{escape(certainty)}">'
        f"{escape(label)} {symbols}"
        "</span>"
    )


def build_sof_html(
    grade_rows: Iterable[Any],
    meta_results: dict[str, SofMetaSummary] | None = None,
) -> str:
    """Render a Summary-of-Findings HTML table.

    Args:
        grade_rows: iterable of GRADE assessment ORM rows (or any object
            exposing ``outcome_label``, ``meta_id``, ``certainty``, ``notes``).
        meta_results: optional ``meta_id`` → ``SofMetaSummary`` lookup. Rows
            with no meta link or a missing key show "narrative synthesis"
            placeholders.
    """
    meta_results = meta_results or {}

    header = (
        "<tr>"
        "<th>Outcome</th>"
        "<th>N studies</th>"
        "<th>Effect estimate (95% CI)</th>"
        "<th>Certainty</th>"
        "<th>Comments</th>"
        "</tr>"
    )

    body_rows: list[str] = []
    for row in grade_rows:
        outcome = escape(getattr(row, "outcome_label", "") or "")
        certainty = getattr(row, "certainty", "low") or "low"
        notes = escape(getattr(row, "notes", "") or "")
        meta_id = getattr(row, "meta_id", None)
        summary = meta_results.get(meta_id) if meta_id else None

        if summary is None:
            n_studies = "&mdash;"
            effect = '<em>Narrative synthesis</em>'
            cite_tokens = ""
        else:
            n_studies = str(int(summary.n_studies))
            effect = escape(
                _fmt_effect(
                    summary.effect_metric,
                    summary.pooled_estimate,
                    summary.ci_low,
                    summary.ci_high,
                )
            ).replace("&amp;mdash;", "&mdash;")
            cite_tokens = " ".join(
                f"[CITE_{escape(aid)}]" for aid in summary.article_ids
            )

        comment_cell = notes
        if cite_tokens:
            sep = " " if comment_cell else ""
            comment_cell = f"{comment_cell}{sep}<small>{cite_tokens}</small>"

        body_rows.append(
            "<tr>"
            f"<td>{outcome}</td>"
            f"<td>{n_studies}</td>"
            f"<td>{effect}</td>"
            f"<td>{_badge(certainty)}</td>"
            f"<td>{comment_cell}</td>"
            "</tr>"
        )

    return (
        '<table class="sof-table">'
        f"<thead>{header}</thead>"
        f"<tbody>{''.join(body_rows)}</tbody>"
        "</table>"
    )
