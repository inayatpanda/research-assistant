"""Leave-one-out sensitivity analysis (Phase 19 / MP19).

For each input study, re-runs the pool with that study excluded and
returns the resulting estimate / CI / I^2 so the UI / push can render a
sensitivity forest figure.
"""
from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Sequence

import matplotlib

matplotlib.use("Agg")  # noqa: E402

import matplotlib.pyplot as plt  # noqa: E402

from .effect_sizes import Effect
from .heterogeneity import heterogeneity
from .pooling import pool


@dataclass(frozen=True)
class LeaveOneOutRow:
    excluded_id: str
    pooled_effect: float
    ci_low: float
    ci_high: float
    i2: float


def leave_one_out(
    effects: Sequence[Effect],
    *,
    ids: Sequence[str],
    model: str,
) -> list[LeaveOneOutRow]:
    """Run leave-one-out sensitivity analysis.

    Returns one row per input study with the pooled effect of the
    remaining studies. Requires ≥ 3 inputs (so each leave-one-out pool
    has ≥ 2 studies).
    """
    if len(effects) != len(ids):
        raise ValueError("effects and ids must have equal length")
    if len(effects) < 3:
        raise ValueError("leave-one-out requires at least 3 input studies")
    out: list[LeaveOneOutRow] = []
    for i, sid in enumerate(ids):
        subset = [e for j, e in enumerate(effects) if j != i]
        pooled = pool(subset, model)
        het = heterogeneity(subset)
        out.append(
            LeaveOneOutRow(
                excluded_id=sid,
                pooled_effect=float(pooled.estimate),
                ci_low=float(pooled.ci_low),
                ci_high=float(pooled.ci_high),
                i2=float(het.i2),
            )
        )
    return out


def render_leave_one_out_png(
    rows: Sequence[LeaveOneOutRow],
    *,
    overall_estimate: float,
    metric_label: str,
    log_scale: bool = False,
    dpi: int = 150,
) -> bytes:
    """Render a sensitivity-style forest plot (one row per excluded study).

    The vertical line marks the *full* meta-analysis estimate; each row
    plots the leave-one-out point estimate with 95% CI bars.
    """
    n = len(rows)
    if n == 0:
        raise ValueError("render_leave_one_out_png needs at least one row")
    fig_h = max(3.0, 0.5 * n + 1.5)
    fig = plt.figure(figsize=(7.0, fig_h), dpi=dpi)
    ax = fig.add_subplot(111)

    ys = list(range(n, 0, -1))
    for y, r in zip(ys, rows):
        err_lo = r.pooled_effect - r.ci_low
        err_hi = r.ci_high - r.pooled_effect
        ax.errorbar(
            r.pooled_effect, y,
            xerr=[[err_lo], [err_hi]],
            fmt="o",
            color="black",
            ecolor="black",
            elinewidth=1.0,
            capsize=2,
        )
        ax.text(
            -0.02, y, f"−{r.excluded_id}",
            transform=ax.get_yaxis_transform(),
            ha="right", va="center",
            fontsize=8,
        )
        ax.text(
            1.02, y, f"{r.pooled_effect:.3f} [{r.ci_low:.3f}, {r.ci_high:.3f}]",
            transform=ax.get_yaxis_transform(),
            ha="left", va="center",
            fontsize=8,
        )

    ax.axvline(overall_estimate, color="grey", linestyle="--", linewidth=0.8)
    if log_scale:
        ax.axvline(0.0, color="red", linestyle=":", linewidth=0.6)
    ax.set_yticks([])
    ax.set_ylim(0.5, n + 0.5)
    ax.set_xlabel(f"{metric_label} (leave-one-out)")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    fig.subplots_adjust(left=0.3, right=0.7, top=0.95, bottom=0.15)
    try:
        buf = BytesIO()
        fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight")
        return buf.getvalue()
    finally:
        fig.clf()
        plt.close(fig)


__all__ = ["LeaveOneOutRow", "leave_one_out", "render_leave_one_out_png"]
