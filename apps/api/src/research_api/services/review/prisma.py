from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Protocol
from xml.sax.saxutils import escape

EXCLUSION_KEYS: tuple[str, ...] = (
    "population",
    "intervention",
    "outcome",
    "study_design",
    "language",
    "duplicate",
    "other",
)


@dataclass(frozen=True)
class PrismaCounts:
    identified: int
    after_dedupe: int
    screened: int
    excluded_title: int
    full_text_assessed: int
    excluded_full: dict[str, int]
    included: int


class _SearchLike(Protocol):
    n_results: int


class _ScreenLike(Protocol):
    article_id: str
    stage: str
    decision: str
    exclusion_category: str | None


def count_flow(
    *,
    search_records: list[Any],
    screening_records: list[Any],
) -> PrismaCounts:
    identified = sum(int(getattr(r, "n_results", 0) or 0) for r in search_records)
    after_dedupe = identified

    title_rows = [r for r in screening_records if r.stage == "title_abstract"]
    full_rows = [r for r in screening_records if r.stage == "full_text"]

    screened = sum(1 for r in title_rows if r.decision != "pending")
    excluded_title = sum(1 for r in title_rows if r.decision == "exclude")

    full_text_assessed = len(full_rows)

    excluded_counter: Counter[str] = Counter()
    for r in full_rows:
        if r.decision == "exclude":
            cat = r.exclusion_category or "other"
            if cat not in EXCLUSION_KEYS:
                cat = "other"
            excluded_counter[cat] += 1
    excluded_full = {k: int(excluded_counter.get(k, 0)) for k in EXCLUSION_KEYS}

    included = sum(1 for r in full_rows if r.decision == "include")

    return PrismaCounts(
        identified=identified,
        after_dedupe=after_dedupe,
        screened=screened,
        excluded_title=excluded_title,
        full_text_assessed=full_text_assessed,
        excluded_full=excluded_full,
        included=included,
    )


_BOX_W = 280
_BOX_H = 70
_COL_X = 200
_EXCL_X = 520


def _box(x: int, y: int, label: str, value: int) -> str:
    label_esc = escape(label)
    return (
        f'<g><rect x="{x}" y="{y}" width="{_BOX_W}" height="{_BOX_H}" '
        f'fill="#ffffff" stroke="#1f2937" stroke-width="1.5" rx="4"/>'
        f'<text x="{x + _BOX_W // 2}" y="{y + 28}" text-anchor="middle" '
        f'font-family="sans-serif" font-size="13" fill="#111827">{label_esc}</text>'
        f'<text x="{x + _BOX_W // 2}" y="{y + 52}" text-anchor="middle" '
        f'font-family="sans-serif" font-size="14" font-weight="700" fill="#111827">'
        f'n = {int(value)}</text></g>'
    )


def _arrow_down(x: int, y_from: int, y_to: int) -> str:
    return (
        f'<line x1="{x}" y1="{y_from}" x2="{x}" y2="{y_to}" '
        f'stroke="#1f2937" stroke-width="1.5" marker-end="url(#arrow)"/>'
    )


def _arrow_right(x_from: int, x_to: int, y: int) -> str:
    return (
        f'<line x1="{x_from}" y1="{y}" x2="{x_to}" y2="{y}" '
        f'stroke="#1f2937" stroke-width="1.5" marker-end="url(#arrow)"/>'
    )


def render_svg(counts: PrismaCounts, *, title: str | None = None) -> str:
    title_text = escape(title) if title else "PRISMA 2020 flow"

    excl_lines: list[str] = []
    for i, key in enumerate(EXCLUSION_KEYS):
        n = int(counts.excluded_full.get(key, 0))
        excl_lines.append(
            f'<tspan x="{_EXCL_X + 12}" dy="{16 if i else 0}">'
            f'{escape(key)}: {n}</tspan>'
        )
    excl_text = "".join(excl_lines)

    boxes = [
        _box(_COL_X, 80, "Records identified", counts.identified),
        _box(_COL_X, 190, "Records after dedupe", counts.after_dedupe),
        _box(_COL_X, 300, "Records screened", counts.screened),
        _box(_COL_X, 430, "Full-text assessed", counts.full_text_assessed),
        _box(_COL_X, 580, "Studies included", counts.included),
        (
            f'<g><rect x="{_EXCL_X}" y="300" width="{_BOX_W}" height="{_BOX_H}" '
            f'fill="#ffffff" stroke="#1f2937" stroke-width="1.5" rx="4"/>'
            f'<text x="{_EXCL_X + _BOX_W // 2}" y="{328}" text-anchor="middle" '
            f'font-family="sans-serif" font-size="13" fill="#111827">'
            f'Excluded at title/abstract</text>'
            f'<text x="{_EXCL_X + _BOX_W // 2}" y="{352}" text-anchor="middle" '
            f'font-family="sans-serif" font-size="14" font-weight="700" fill="#111827">'
            f'n = {int(counts.excluded_title)}</text></g>'
        ),
        (
            f'<g><rect x="{_EXCL_X}" y="430" width="{_BOX_W}" height="{160}" '
            f'fill="#ffffff" stroke="#1f2937" stroke-width="1.5" rx="4"/>'
            f'<text x="{_EXCL_X + 12}" y="450" font-family="sans-serif" '
            f'font-size="13" fill="#111827">Excluded at full text</text>'
            f'<text y="475" font-family="sans-serif" font-size="11" fill="#111827">'
            f'{excl_text}</text></g>'
        ),
    ]

    arrows = [
        _arrow_down(_COL_X + _BOX_W // 2, 150, 188),
        _arrow_down(_COL_X + _BOX_W // 2, 260, 298),
        _arrow_down(_COL_X + _BOX_W // 2, 370, 428),
        _arrow_down(_COL_X + _BOX_W // 2, 500, 578),
        _arrow_right(_COL_X + _BOX_W, _EXCL_X, 335),
        _arrow_right(_COL_X + _BOX_W, _EXCL_X, 510),
    ]

    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 720" '
        'width="800" height="720">',
        '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" '
        'markerWidth="8" markerHeight="8" orient="auto-start-reverse">'
        '<path d="M 0 0 L 10 5 L 0 10 z" fill="#1f2937"/></marker></defs>',
        f'<title>{title_text}</title>',
        f'<text x="400" y="40" text-anchor="middle" font-family="sans-serif" '
        f'font-size="18" font-weight="700" fill="#111827">{title_text}</text>',
        *boxes,
        *arrows,
        '</svg>',
    ]
    return "".join(parts)
