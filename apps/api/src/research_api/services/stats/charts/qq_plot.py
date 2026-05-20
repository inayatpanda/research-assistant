"""QQ plot for normality diagnostic — Phase 8.5 Task 4."""
from __future__ import annotations

import html
from typing import Any

import pandas as pd
from scipy import stats as sp_stats

from ._base import fig_context, fig_to_data_uri


def render_qq_plot(
    *,
    df: pd.DataFrame,
    column: str,
    title_suffix: str | None = None,
    display_labels: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Probability plot (Q-Q against normal). Theoretical quantiles vs sample."""
    if column not in df.columns:
        raise ValueError(f"QQ plot requires column {column!r}")
    series = pd.to_numeric(df[column], errors="coerce").dropna()
    if series.empty:
        raise ValueError("QQ plot: column is empty after NaN drop")

    safe_suffix = html.escape(title_suffix) if title_suffix else None

    with fig_context() as fig:
        ax = fig.add_subplot(1, 1, 1)
        sp_stats.probplot(series.to_numpy(dtype=float), dist="norm", plot=ax)
        # Recolour the reference line for consistency with the seaborn theme.
        lines = ax.get_lines()
        if len(lines) >= 2:
            lines[0].set_markerfacecolor("#3b82f6")
            lines[0].set_markeredgecolor("#3b82f6")
            lines[1].set_color("#ef4444")
        dl = display_labels or {}
        col_label = dl.get(column, column)
        ax.set_xlabel("Theoretical quantiles")
        ax.set_ylabel(f"Sample quantiles ({col_label})")
        title = "Normal Q-Q plot"
        if safe_suffix:
            title = f"{title} — {safe_suffix}"
        ax.set_title(title)
        return fig_to_data_uri(fig)
