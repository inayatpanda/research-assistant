"""Scatter + regression fit plot — Phase 8.5 Task 5."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import seaborn as sns

from ._base import fig_context, fig_to_data_uri


def render_scatter_plot(
    *,
    df: pd.DataFrame,
    x: str,
    y: str,
    fit: str = "linear",  # 'linear' | 'lowess' | 'none'
    ci: int | None = 95,
) -> dict[str, Any]:
    """Seaborn scatter + (optional) fit line + bootstrap CI band."""
    if x not in df.columns or y not in df.columns:
        raise ValueError(f"scatter plot requires {x!r} and {y!r} columns")
    sub = df[[x, y]].copy()
    sub[x] = pd.to_numeric(sub[x], errors="coerce")
    sub[y] = pd.to_numeric(sub[y], errors="coerce")
    sub = sub.dropna()
    if sub.empty:
        raise ValueError("scatter plot: dataframe is empty after NaN drop")

    # If the predictor is constant, regplot/lowess cannot fit a slope. Fall back
    # to a plain scatter without a fit line.
    constant_x = bool(np.isclose(np.var(sub[x].to_numpy(dtype=float)), 0.0))
    if constant_x:
        fit = "none"

    with fig_context() as fig:
        ax = fig.add_subplot(1, 1, 1)
        if fit == "lowess":
            sns.regplot(
                data=sub,
                x=x,
                y=y,
                lowess=True,
                ax=ax,
                scatter_kws={"alpha": 0.55, "s": 22},
                line_kws={"color": "#ef4444"},
                ci=ci,
            )
        elif fit == "linear":
            sns.regplot(
                data=sub,
                x=x,
                y=y,
                ax=ax,
                scatter_kws={"alpha": 0.55, "s": 22},
                line_kws={"color": "#ef4444"},
                ci=ci,
            )
        else:
            sns.scatterplot(data=sub, x=x, y=y, ax=ax, alpha=0.55, s=22)
        ax.set_xlabel(x)
        ax.set_ylabel(y)
        return fig_to_data_uri(fig)
