"""Box + strip plot renderer for group-comparison tests — Phase 8.5 Task 2."""
from __future__ import annotations

import html
from typing import Any

import pandas as pd
import seaborn as sns

from ._base import fig_context, fig_to_data_uri


def render_box_plot(
    *,
    df: pd.DataFrame,
    outcome: str,
    groups: str,
    title: str | None = None,
    display_labels: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Seaborn box+strip plot. One box per group on the categorical axis,
    outcome on the numeric axis.

    ``display_labels`` (DEMO-FIX-C) overrides the axis text — typical usage
    is ``{outcome_col: "VAS Pain at 6 months", groups_col: "BMI band"}``.
    Falls back to the canonical column name when not provided.
    """
    if outcome not in df.columns or groups not in df.columns:
        raise ValueError(
            f"box plot requires both {outcome!r} and {groups!r} columns"
        )
    sub = df[[outcome, groups]].dropna()
    if sub.empty:
        raise ValueError("box plot: dataframe is empty after NaN drop")

    levels = sorted(sub[groups].dropna().unique().tolist(), key=str)
    if len(levels) < 2:
        raise ValueError(
            f"box plot needs at least 2 levels in {groups!r}, got {len(levels)}"
        )

    safe_title = html.escape(title) if title else None
    dl = display_labels or {}
    x_label = dl.get(groups, groups)
    y_label = dl.get(outcome, outcome)

    with fig_context() as fig:
        ax = fig.add_subplot(1, 1, 1)
        sns.boxplot(
            data=sub,
            x=groups,
            y=outcome,
            order=levels,
            ax=ax,
            fliersize=0,
            linewidth=1.0,
        )
        sns.stripplot(
            data=sub,
            x=groups,
            y=outcome,
            order=levels,
            ax=ax,
            color="black",
            alpha=0.35,
            size=3,
            jitter=True,
        )
        ax.set_xlabel(x_label)
        ax.set_ylabel(y_label)
        if safe_title:
            ax.set_title(safe_title)
        return fig_to_data_uri(fig)
