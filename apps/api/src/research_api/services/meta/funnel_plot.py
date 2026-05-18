"""Funnel plot renderer — effect (x) vs SE (y, inverted)."""
from __future__ import annotations

from io import BytesIO
from typing import Sequence

import matplotlib

matplotlib.use("Agg")  # noqa: E402

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

from .effect_sizes import Effect

_Z975 = 1.959964


def _build_figure(
    *,
    effects: Sequence[Effect],
    pooled_estimate: float,
    metric_label: str,
    log_scale: bool,
) -> Figure:
    fig = plt.figure(figsize=(6.0, 6.0), dpi=150)
    ax = fig.add_subplot(111)

    xs = [e.yi for e in effects]
    ses = [e.se for e in effects]
    ax.scatter(xs, ses, color="black", s=40, zorder=3)

    # Pseudo-95% CI funnel: pooled ± 1.96*SE across the SE axis
    if ses:
        se_max = max(ses) * 1.1
        se_grid = np.linspace(0.0, se_max, 50)
        left = pooled_estimate - _Z975 * se_grid
        right = pooled_estimate + _Z975 * se_grid
        ax.plot(left, se_grid, color="grey", linestyle="--", linewidth=0.8)
        ax.plot(right, se_grid, color="grey", linestyle="--", linewidth=0.8)
        ax.axvline(pooled_estimate, color="black", linestyle="-", linewidth=0.8)
        ax.set_ylim(se_max, 0.0)  # invert: SE=0 at top
    else:
        ax.set_ylim(1.0, 0.0)

    if log_scale:
        ax.set_xlabel(f"{metric_label} (log scale; null at 0)")
    else:
        ax.set_xlabel(metric_label)
    ax.set_ylabel("Standard error")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    return fig


def render_funnel_png(
    *,
    effects: Sequence[Effect],
    pooled_estimate: float,
    metric_label: str,
    log_scale: bool,
    dpi: int = 150,
) -> bytes:
    fig = _build_figure(
        effects=effects,
        pooled_estimate=pooled_estimate,
        metric_label=metric_label,
        log_scale=log_scale,
    )
    try:
        buf = BytesIO()
        fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight")
        return buf.getvalue()
    finally:
        fig.clf()
        plt.close(fig)
