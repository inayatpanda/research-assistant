"""Single-variable histogram + categorical counts renderers — Phase 8.5 Task 3."""
from __future__ import annotations

from typing import Any

import pandas as pd
import seaborn as sns

from ._base import fig_context, fig_to_data_uri


def render_histogram(
    *,
    df: pd.DataFrame,
    column: str,
    bins: int | str = "auto",
    kde: bool = True,
    display_labels: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Seaborn histplot with optional KDE overlay.

    ``display_labels`` (DEMO-FIX-C) maps canonical column names → human
    labels for the x-axis text.
    """
    if column not in df.columns:
        raise ValueError(f"histogram requires column {column!r}")
    series = pd.to_numeric(df[column], errors="coerce").dropna()
    if series.empty:
        raise ValueError("histogram: column is empty after NaN drop")

    dl = display_labels or {}
    x_label = dl.get(column, column)

    with fig_context() as fig:
        ax = fig.add_subplot(1, 1, 1)
        sns.histplot(series, bins=bins, kde=kde, ax=ax, color="#3b82f6")
        ax.set_xlabel(x_label)
        ax.set_ylabel("Count")
        return fig_to_data_uri(fig)


def render_categorical_counts(
    *,
    df: pd.DataFrame,
    var_a: str,
    var_b: str,
    display_labels: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Side-by-side bar plot: counts of var_a across levels of var_b.

    ``display_labels`` (DEMO-FIX-C) overrides x-axis + legend title.
    """
    if var_a not in df.columns or var_b not in df.columns:
        raise ValueError(
            f"categorical counts requires {var_a!r} and {var_b!r} columns"
        )
    sub = df[[var_a, var_b]].dropna()
    if sub.empty:
        raise ValueError("categorical counts: dataframe is empty after NaN drop")

    counts = (
        sub.groupby([var_a, var_b]).size().reset_index(name="count")  # type: ignore[arg-type]
    )

    dl = display_labels or {}
    x_label = dl.get(var_a, var_a)
    legend_label = dl.get(var_b, var_b)

    with fig_context() as fig:
        ax = fig.add_subplot(1, 1, 1)
        sns.barplot(data=counts, x=var_a, y="count", hue=var_b, ax=ax)
        ax.set_xlabel(x_label)
        ax.set_ylabel("Count")
        ax.legend(title=legend_label, loc="best", fontsize=9)
        return fig_to_data_uri(fig)
