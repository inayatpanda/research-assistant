"""Narrative synthesis HTML builder (Phase 19 / MP19).

Pure function: builds a multi-instrument comparison table from a list of
narrative-synthesis entries. One row per (outcome, instrument); columns
include direction, range, narrative cell, and citation list.
"""
from __future__ import annotations

from html import escape
from typing import Iterable, Mapping, Sequence


def _direction_arrow(direction: str) -> str:
    return {
        "higher_better": "↑",
        "lower_better": "↓",
        "neutral": "·",
    }.get(direction, "·")


def build_narrative_table_html(entries: Iterable[Mapping]) -> str:
    """Render a narrative-synthesis comparison table as HTML.

    ``entries`` may be Pydantic-validated dicts or ORM rows mapped to
    dict-like objects; each entry must expose: ``outcome_label``,
    ``instrument``, ``range_text``, ``direction``, ``narrative_html``,
    ``study_citations`` (a list of article_ids).

    Output is a single ``<table class="narrative-synthesis-table">``
    block. Each cell escapes researcher-controlled strings except
    ``narrative_html`` which is treated as trusted (the FE sanitises
    via DOMPurify before persistence).

    Citation tokens are emitted as ``[CITE_<article_id>]`` so the
    downstream ``replace_cite_tokens_with_markup`` pipeline can pick
    them up.
    """
    rows: list[str] = []
    for entry in entries:
        outcome = escape(_get(entry, "outcome_label", default=""))
        instrument = escape(_get(entry, "instrument", default=""))
        range_text = escape(_get(entry, "range_text", default="") or "")
        direction = _direction_arrow(_get(entry, "direction", default="neutral"))
        narrative = _get(entry, "narrative_html", default="") or ""
        citations: Sequence[str] = _get(entry, "study_citations", default=[]) or []
        cite_tokens = " ".join(
            f"[CITE_{escape(str(c))}]" for c in citations if c
        )
        rows.append(
            "<tr>"
            f"<td>{outcome}</td>"
            f"<td>{instrument}</td>"
            f'<td class="ns-range">{range_text}</td>'
            f'<td class="ns-direction">{direction}</td>'
            f'<td class="ns-narrative">{narrative}</td>'
            f'<td class="ns-citations">{cite_tokens}</td>'
            "</tr>"
        )
    return (
        '<table class="narrative-synthesis-table">'
        "<thead><tr>"
        "<th>Outcome</th><th>Instrument</th><th>Range</th>"
        "<th>Direction</th><th>Narrative</th><th>Studies</th>"
        "</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody>"
        "</table>"
    )


def build_outcome_instruments_table_html(rows: Iterable[Mapping]) -> str:
    """Render a many-to-many studies × instruments comparison grid.

    Each row in the input represents one instrument; ``study_values`` is
    a list of per-study cells (article_id, group_label, value, sd_or_ci,
    n). The output table arranges studies as columns when possible —
    falling back to one-row-per-cell when the study set is sparse.
    """
    instrument_rows: list[dict] = []
    article_order: list[str] = []
    seen_articles: set[str] = set()
    for r in rows:
        sv = _get(r, "study_values", default=[]) or []
        instrument_rows.append({
            "outcome": _get(r, "outcome_label", default=""),
            "instrument": _get(r, "instrument_name", default=""),
            "low": _get(r, "score_range_low", default=None),
            "high": _get(r, "score_range_high", default=None),
            "mid": _get(r, "mid", default=None),
            "values": sv,
        })
        for cell in sv:
            aid = (
                cell.get("article_id") if isinstance(cell, dict) else None
            )
            if aid and aid not in seen_articles:
                seen_articles.add(aid)
                article_order.append(aid)

    header_studies = "".join(
        f"<th>[CITE_{escape(str(aid))}]</th>" for aid in article_order
    )
    header = (
        "<tr>"
        "<th>Outcome</th><th>Instrument</th><th>Range</th><th>MID</th>"
        f"{header_studies}"
        "</tr>"
    )

    body_rows: list[str] = []
    for ir in instrument_rows:
        outcome = escape(ir["outcome"])
        instr = escape(ir["instrument"])
        if ir["low"] is None and ir["high"] is None:
            rng = ""
        else:
            rng = f"{ir['low'] if ir['low'] is not None else ''}–{ir['high'] if ir['high'] is not None else ''}"
        mid = "" if ir["mid"] is None else f"{ir['mid']}"
        # Index per-study cells by article_id for fast lookup
        by_aid: dict[str, dict] = {}
        for cell in ir["values"]:
            if isinstance(cell, dict):
                aid = cell.get("article_id")
                if aid:
                    by_aid[aid] = cell
        cells: list[str] = []
        for aid in article_order:
            cell = by_aid.get(aid)
            if cell is None:
                cells.append('<td class="ns-na">—</td>')
                continue
            value = cell.get("value")
            sd_or_ci = cell.get("sd_or_ci") or ""
            n = cell.get("n")
            group = cell.get("group_label", "")
            value_str = "" if value is None else f"{value}"
            n_str = "" if n is None else f"n={n}"
            cell_html = " ".join(
                p for p in (escape(str(group)), escape(value_str), escape(str(sd_or_ci)), escape(n_str)) if p
            )
            cells.append(f"<td>{cell_html}</td>")
        body_rows.append(
            "<tr>"
            f"<td>{outcome}</td>"
            f"<td>{instr}</td>"
            f"<td>{escape(rng)}</td>"
            f"<td>{escape(mid)}</td>"
            f"{''.join(cells)}"
            "</tr>"
        )

    return (
        '<table class="outcome-instruments-table">'
        f"<thead>{header}</thead>"
        f"<tbody>{''.join(body_rows)}</tbody>"
        "</table>"
    )


def _get(entry, key, *, default=None):
    if isinstance(entry, dict):
        return entry.get(key, default)
    return getattr(entry, key, default)


__all__ = ["build_narrative_table_html", "build_outcome_instruments_table_html"]
