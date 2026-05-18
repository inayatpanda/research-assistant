"""Forest plot renderer — PNG bytes via matplotlib Agg backend."""
from __future__ import annotations

import math
from dataclasses import dataclass
from io import BytesIO
from typing import Sequence

import matplotlib

matplotlib.use("Agg")  # noqa: E402

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402


@dataclass(frozen=True)
class ForestRow:
    label: str
    yi: float
    ci_low: float
    ci_high: float
    weight_pct: float
    subgroup: str | None


def _build_figure(
    *,
    rows: Sequence[ForestRow],
    pooled_estimate: float,
    pooled_ci_low: float,
    pooled_ci_high: float,
    metric_label: str,
    log_scale: bool,
    favours_left: str | None,
    favours_right: str | None,
    subgroup_summaries: dict[str, tuple[float, float, float]] | None = None,
) -> Figure:
    """Construct and return a matplotlib Figure (caller is responsible for closing)."""
    # Order rows by subgroup if subgroup_summaries is provided
    if subgroup_summaries:
        ordered: list[ForestRow] = []
        for sg in subgroup_summaries.keys():
            ordered.extend(r for r in rows if r.subgroup == sg)
        # Any rows with subgroups not in the summary dict tack on the end
        for r in rows:
            if r not in ordered:
                ordered.append(r)
        rows_sorted = ordered
        n_extra = len(subgroup_summaries)
    else:
        rows_sorted = list(rows)
        n_extra = 0

    k = len(rows_sorted)
    # Height scales with rows + extras (subgroup diamonds + pooled diamond + headers/labels)
    fig_h = max(4.0, 0.5 * (k + 4)) + 0.6 * n_extra
    fig = plt.figure(figsize=(8.0, fig_h), dpi=150)
    ax = fig.add_subplot(111)

    # Plot rows top-to-bottom: row index 0 at top means high y.
    # We'll plot at y positions reversed so largest y is the top row.
    n_total = k + (1 + n_extra)  # rows + pooled diamond + subgroup diamonds
    y_positions: dict[int, float] = {}
    cursor = float(n_total)

    current_subgroup: str | None = None
    rendered_subgroup_summaries: list[tuple[str, float, float, float, float]] = []
    for idx, r in enumerate(rows_sorted):
        if subgroup_summaries and r.subgroup != current_subgroup:
            current_subgroup = r.subgroup
            # Reserve a y slot for the subgroup label (we don't decrement here; the diamond
            # is appended after the subgroup block)
        y_positions[idx] = cursor
        cursor -= 1.0

    # Now render rows
    for idx, r in enumerate(rows_sorted):
        y = y_positions[idx]
        err_left = r.yi - r.ci_low
        err_right = r.ci_high - r.yi
        size = max(20.0, min(300.0, r.weight_pct * 5.0))
        ax.errorbar(
            r.yi, y,
            xerr=[[err_left], [err_right]],
            fmt="s",
            markersize=math.sqrt(size),
            color="black",
            ecolor="black",
            elinewidth=1.0,
            capsize=2,
        )
        ax.text(
            -0.02, y, r.label,
            transform=ax.get_yaxis_transform(),
            ha="right", va="center",
            fontsize=8,
        )
        ax.text(
            1.02, y, f"{r.yi:.2f} [{r.ci_low:.2f}, {r.ci_high:.2f}]  {r.weight_pct:.1f}%",
            transform=ax.get_yaxis_transform(),
            ha="left", va="center",
            fontsize=8,
        )

    # Subgroup diamonds (one per subgroup level)
    if subgroup_summaries:
        for sg, (sg_yi, sg_lo, sg_hi) in subgroup_summaries.items():
            cursor -= 1.0
            y = cursor
            _draw_diamond(ax, y, sg_yi, sg_lo, sg_hi, color="#444", height=0.3)
            ax.text(
                -0.02, y, f"Subtotal ({sg})",
                transform=ax.get_yaxis_transform(),
                ha="right", va="center",
                fontsize=8, fontstyle="italic",
            )
            rendered_subgroup_summaries.append((sg, sg_yi, sg_lo, sg_hi, y))

    # Pooled diamond at the bottom
    cursor -= 1.0
    pooled_y = cursor
    _draw_diamond(ax, pooled_y, pooled_estimate, pooled_ci_low, pooled_ci_high, color="black", height=0.4)
    ax.text(
        -0.02, pooled_y, "Pooled",
        transform=ax.get_yaxis_transform(),
        ha="right", va="center",
        fontsize=9, fontweight="bold",
    )

    # Vertical reference at null. For log-scale metrics, the analysis scale is log(yi),
    # so the null is 0 on that axis (since exp(0)=1).
    null_x = 0.0
    ax.axvline(null_x, color="grey", linewidth=0.7, linestyle="--")

    # Axes cosmetics
    ax.set_yticks([])
    ax.set_ylim(pooled_y - 1.0, n_total + 0.5)
    # X range that accommodates all CI bounds with padding
    all_lo = [r.ci_low for r in rows_sorted] + [pooled_ci_low]
    all_hi = [r.ci_high for r in rows_sorted] + [pooled_ci_high]
    if subgroup_summaries:
        for _, lo, hi in subgroup_summaries.values():
            all_lo.append(lo)
            all_hi.append(hi)
    xmin = min(all_lo) - 0.2
    xmax = max(all_hi) + 0.2
    # Ensure null is visible
    xmin = min(xmin, -0.1)
    xmax = max(xmax, 0.1)
    ax.set_xlim(xmin, xmax)

    # X label
    if log_scale:
        ax.set_xlabel(f"{metric_label} (log scale; null at 0)")
    else:
        ax.set_xlabel(metric_label)

    if favours_left or favours_right:
        text = ""
        if favours_left:
            text += f"← {favours_left}"
        text += "        "
        if favours_right:
            text += f"{favours_right} →"
        ax.text(0.5, -0.1, text.strip(), transform=ax.transAxes, ha="center", fontsize=8)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)

    fig.subplots_adjust(left=0.25, right=0.75, top=0.95, bottom=0.12)
    return fig


def _draw_diamond(ax, y: float, x: float, x_low: float, x_high: float, *, color: str, height: float) -> None:
    """Draw a small diamond polygon at (x, y) extending horizontally from x_low to x_high."""
    half = height / 2.0
    diamond_x = [x_low, x, x_high, x, x_low]
    diamond_y = [y, y + half, y, y - half, y]
    ax.fill(diamond_x, diamond_y, color=color, alpha=0.85)


def render_forest_png(
    *,
    rows: Sequence[ForestRow],
    pooled_estimate: float,
    pooled_ci_low: float,
    pooled_ci_high: float,
    metric_label: str,
    log_scale: bool,
    favours_left: str | None,
    favours_right: str | None,
    subgroup_summaries: dict[str, tuple[float, float, float]] | None = None,
    dpi: int = 150,
) -> bytes:
    """Pure function: render a forest plot and return PNG bytes."""
    fig = _build_figure(
        rows=rows,
        pooled_estimate=pooled_estimate,
        pooled_ci_low=pooled_ci_low,
        pooled_ci_high=pooled_ci_high,
        metric_label=metric_label,
        log_scale=log_scale,
        favours_left=favours_left,
        favours_right=favours_right,
        subgroup_summaries=subgroup_summaries,
    )
    try:
        buf = BytesIO()
        fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight")
        return buf.getvalue()
    finally:
        fig.clf()
        plt.close(fig)
