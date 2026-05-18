"""Render a ConsortFlow into a CONSORT 2010 SVG flow diagram.

Same hand-rolled approach as services/review/prisma.py — we assemble a fixed
grid of <rect> + <text> nodes via f-strings. No third-party SVG library; the
output validates as SVG 1.1 and parses via xml.etree.ElementTree.

Layout (vertical):
  1. Enrollment (Assessed for eligibility)
     ─→ Excluded (with optional Reasons sub-list)
  2. Randomised
  3. Allocation: Intervention | Control side-by-side
  4. Follow-up: lost-to-follow-up + discontinued per arm
  5. Analysis: per arm
"""
from __future__ import annotations

from xml.sax.saxutils import escape

from .counter import ConsortFlow


_BOX_W = 230
_BOX_H = 56
_GAP = 30

_LEFT_X = 80           # intervention arm
_RIGHT_X = 430         # control arm
_CENTER_X = (_LEFT_X + _RIGHT_X) // 2
_EXCL_X = 760

_VIEW_W = 1040
_VIEW_H = 980


def _fmt(value: int | None) -> str:
    return "—" if value is None else f"n = {int(value)}"


def _box(x: int, y: int, label: str, value: int | None, *, w: int = _BOX_W, h: int = _BOX_H) -> str:
    label_esc = escape(label)
    return (
        f'<g><rect x="{x}" y="{y}" width="{w}" height="{h}" '
        f'fill="#ffffff" stroke="#1f2937" stroke-width="1.5" rx="4"/>'
        f'<text x="{x + w // 2}" y="{y + 22}" text-anchor="middle" '
        f'font-family="sans-serif" font-size="12" fill="#111827">{label_esc}</text>'
        f'<text x="{x + w // 2}" y="{y + 42}" text-anchor="middle" '
        f'font-family="sans-serif" font-size="13" font-weight="700" fill="#111827">'
        f'{_fmt(value)}</text></g>'
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


def _reasons_block(x: int, y: int, reasons: dict[str, int]) -> str:
    """Render the right-side reasons-for-exclusion box. Untrusted user input —
    every label is html-escaped before interpolation."""
    lines: list[str] = []
    for i, (reason, count) in enumerate(reasons.items()):
        label = escape(str(reason))
        lines.append(
            f'<tspan x="{x + 12}" dy="{18 if i else 18}">'
            f'• {label}: {int(count)}</tspan>'
        )
    line_count = max(1, len(reasons))
    box_h = max(_BOX_H, 36 + 18 * line_count)
    body_text = "".join(lines)
    return (
        f'<g><rect x="{x}" y="{y}" width="{_BOX_W}" height="{box_h}" '
        f'fill="#ffffff" stroke="#1f2937" stroke-width="1.5" rx="4"/>'
        f'<text x="{x + _BOX_W // 2}" y="{y + 22}" text-anchor="middle" '
        f'font-family="sans-serif" font-size="12" fill="#111827">Reasons</text>'
        f'<text font-family="sans-serif" font-size="11" fill="#111827">'
        f'{body_text}</text></g>'
    )


def render_consort_svg(flow: ConsortFlow, *, title: str | None = None) -> str:
    title_text = escape(title) if title else "CONSORT 2010 flow diagram"

    # Row y-coordinates
    y_assessed = 70
    y_random = y_assessed + _BOX_H + _GAP * 2
    y_allocated = y_random + _BOX_H + _GAP * 2
    y_received = y_allocated + _BOX_H + _GAP
    y_followup_lost = y_received + _BOX_H + _GAP
    y_followup_disc = y_followup_lost + _BOX_H + _GAP
    y_analysed = y_followup_disc + _BOX_H + _GAP

    boxes: list[str] = [
        # 1. Enrollment
        _box(_CENTER_X - _BOX_W // 2, y_assessed, "Assessed for eligibility", flow.assessed),
        _box(_EXCL_X, y_assessed, "Excluded", flow.excluded),
        # 2. Randomised
        _box(_CENTER_X - _BOX_W // 2, y_random, "Randomised", flow.randomised),
        # 3. Allocation
        _box(_LEFT_X, y_allocated, "Allocated to intervention", flow.allocated.get("intervention")),
        _box(_RIGHT_X, y_allocated, "Allocated to control", flow.allocated.get("control")),
        _box(_LEFT_X, y_received, "Received intervention", flow.received.get("intervention")),
        _box(_RIGHT_X, y_received, "Received control", flow.received.get("control")),
        # 4. Follow-up
        _box(_LEFT_X, y_followup_lost, "Lost to follow-up", flow.lost_followup.get("intervention")),
        _box(_RIGHT_X, y_followup_lost, "Lost to follow-up", flow.lost_followup.get("control")),
        _box(_LEFT_X, y_followup_disc, "Discontinued", flow.discontinued.get("intervention")),
        _box(_RIGHT_X, y_followup_disc, "Discontinued", flow.discontinued.get("control")),
        # 5. Analysis
        _box(_LEFT_X, y_analysed, "Analysed (intervention)", flow.analysed.get("intervention")),
        _box(_RIGHT_X, y_analysed, "Analysed (control)", flow.analysed.get("control")),
    ]

    if flow.excluded_reasons:
        boxes.append(_reasons_block(_EXCL_X, y_assessed + _BOX_H + 14, flow.excluded_reasons))

    arrows: list[str] = [
        # Assessed → Randomised
        _arrow_down(_CENTER_X, y_assessed + _BOX_H, y_random - 2),
        # Assessed → Excluded (side)
        _arrow_right(
            _CENTER_X + _BOX_W // 2,
            _EXCL_X,
            y_assessed + _BOX_H // 2,
        ),
        # Randomised → Allocated I + C (Y junction)
        _arrow_down(_CENTER_X, y_random + _BOX_H, y_allocated - 2),
        _arrow_down(
            _LEFT_X + _BOX_W // 2,
            y_allocated - 2,
            y_allocated - 2,
        ),  # mostly cosmetic spacer
        # Allocated → Received per arm
        _arrow_down(_LEFT_X + _BOX_W // 2, y_allocated + _BOX_H, y_received - 2),
        _arrow_down(_RIGHT_X + _BOX_W // 2, y_allocated + _BOX_H, y_received - 2),
        # Received → Lost
        _arrow_down(_LEFT_X + _BOX_W // 2, y_received + _BOX_H, y_followup_lost - 2),
        _arrow_down(_RIGHT_X + _BOX_W // 2, y_received + _BOX_H, y_followup_lost - 2),
        # Lost → Discontinued
        _arrow_down(_LEFT_X + _BOX_W // 2, y_followup_lost + _BOX_H, y_followup_disc - 2),
        _arrow_down(_RIGHT_X + _BOX_W // 2, y_followup_lost + _BOX_H, y_followup_disc - 2),
        # Discontinued → Analysed
        _arrow_down(_LEFT_X + _BOX_W // 2, y_followup_disc + _BOX_H, y_analysed - 2),
        _arrow_down(_RIGHT_X + _BOX_W // 2, y_followup_disc + _BOX_H, y_analysed - 2),
    ]

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {_VIEW_W} {_VIEW_H}" '
        f'width="{_VIEW_W}" height="{_VIEW_H}">',
        '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" '
        'markerWidth="8" markerHeight="8" orient="auto-start-reverse">'
        '<path d="M 0 0 L 10 5 L 0 10 z" fill="#1f2937"/></marker></defs>',
        f'<title>{title_text}</title>',
        f'<text x="{_VIEW_W // 2}" y="36" text-anchor="middle" font-family="sans-serif" '
        f'font-size="18" font-weight="700" fill="#111827">{title_text}</text>',
        *boxes,
        *arrows,
        '</svg>',
    ]
    return "".join(parts)
