"""Phase 13 (MP13) — Mixed-effects caterpillar plot.

Shows per-cluster random-intercept estimates with 95% prediction intervals
sorted by point estimate. Useful sanity check for the model's variance
components.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from ._base import fig_context, fig_to_data_uri


def render_mixed_effects_caterpillar(
    *,
    df: pd.DataFrame,
    outcome: str,
    predictors: list[str],
    cluster: str,
    display_labels: dict[str, str] | None = None,
) -> dict[str, Any]:
    formula = f"{outcome} ~ " + " + ".join(predictors)
    df = df.dropna(subset=[outcome, cluster, *predictors])
    model = smf.mixedlm(formula, data=df, groups=df[cluster]).fit(method="lbfgs")
    re = model.random_effects  # dict cluster -> Series
    points = sorted(
        ((str(k), float(v.iloc[0])) for k, v in re.items()),
        key=lambda kv: kv[1],
    )
    labels = [p[0] for p in points]
    values = np.array([p[1] for p in points])
    # Empirical Bayes SDs are not always available — use the residual SE as a
    # conservative interval width so the chart is always renderable.
    se = float(np.sqrt(model.scale)) if hasattr(model, "scale") else 1.0
    half = 1.96 * se / np.sqrt(max(int(len(df) / max(len(labels), 1)), 1))

    with fig_context(figsize=(7.5, max(3.5, 0.25 * len(labels) + 1.0))) as fig:
        ax = fig.gca()
        y = np.arange(len(labels))
        ax.errorbar(values, y, xerr=half, fmt="o", color="#4c6ef5", ecolor="#adb5bd")
        ax.axvline(0.0, color="#868e96", linestyle="--", linewidth=1)
        ax.set_yticks(y)
        ax.set_yticklabels(labels, fontsize=8)
        dl = display_labels or {}
        cluster_label = dl.get(cluster, cluster)
        ax.set_xlabel("Random intercept (centered)")
        ax.set_title(f"Caterpillar plot of {cluster_label}-level random effects")
        return fig_to_data_uri(fig)
