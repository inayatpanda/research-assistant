"""Weighted meta-regression (Phase 19 / MP19).

Single-moderator weighted-least-squares regression of effect size on a
continuous moderator. Uses statsmodels' WLS with weights = 1/(vi + tau²)
when a random-effects model is requested, or 1/vi for fixed-effect.
Returns coefficient, SE, p, R² and a bubble plot.
"""
from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Sequence

import matplotlib

matplotlib.use("Agg")  # noqa: E402

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import statsmodels.api as sm  # noqa: E402

from .effect_sizes import Effect
from .heterogeneity import heterogeneity


@dataclass(frozen=True)
class MetaRegressionResult:
    intercept: float
    coef: float
    se: float
    p: float
    r2: float
    n: int
    bubble_plot_png: bytes


def _wls(effects: Sequence[Effect], moderator: Sequence[float], *, model: str):
    if len(effects) != len(moderator):
        raise ValueError("effects and moderator must have equal length")
    if len(effects) < 3:
        raise ValueError("meta-regression requires at least 3 studies")
    ys = np.array([e.yi for e in effects], dtype=float)
    vis = np.array([e.vi for e in effects], dtype=float)
    xs = np.array(list(moderator), dtype=float)
    if model == "random":
        tau2 = heterogeneity(effects).tau2
        weights = 1.0 / (vis + tau2)
    elif model == "fixed":
        weights = 1.0 / vis
    else:
        raise ValueError(f"unknown model: {model!r}")
    design = sm.add_constant(xs)
    fit = sm.WLS(ys, design, weights=weights).fit()
    return fit, xs, ys, weights


def _bubble_png(
    xs: np.ndarray,
    ys: np.ndarray,
    weights: np.ndarray,
    fit,
    *,
    moderator_label: str,
    metric_label: str,
    dpi: int = 150,
) -> bytes:
    fig = plt.figure(figsize=(6.0, 4.5), dpi=dpi)
    ax = fig.add_subplot(111)
    # Bubble area ∝ weight
    if weights.max() > 0:
        sizes = 40.0 + 200.0 * (weights / weights.max())
    else:
        sizes = np.full_like(weights, 80.0)
    ax.scatter(xs, ys, s=sizes, alpha=0.6, edgecolor="black", facecolor="#4682B4")

    if len(xs) >= 2:
        x_grid = np.linspace(float(xs.min()), float(xs.max()), 100)
        design = sm.add_constant(x_grid)
        y_hat = fit.predict(design)
        ax.plot(x_grid, y_hat, color="black", linewidth=1.2)

    ax.set_xlabel(moderator_label)
    ax.set_ylabel(metric_label)
    ax.axhline(0.0, color="grey", linestyle="--", linewidth=0.6)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.subplots_adjust(left=0.15, right=0.95, top=0.95, bottom=0.15)
    try:
        buf = BytesIO()
        fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight")
        return buf.getvalue()
    finally:
        fig.clf()
        plt.close(fig)


def meta_regression(
    effects: Sequence[Effect],
    moderator: Sequence[float],
    *,
    model: str = "random",
    moderator_label: str = "Moderator",
    metric_label: str = "Effect",
) -> MetaRegressionResult:
    """Single-moderator weighted meta-regression.

    Coefficient is the slope of effect on moderator; p is the two-sided
    Wald-test p-value; R² is the adjusted R² from the WLS fit.
    """
    fit, xs, ys, weights = _wls(effects, moderator, model=model)
    intercept = float(fit.params[0])
    coef = float(fit.params[1])
    se = float(fit.bse[1])
    p = float(fit.pvalues[1])
    r2 = float(fit.rsquared)
    png = _bubble_png(
        xs, ys, weights, fit,
        moderator_label=moderator_label,
        metric_label=metric_label,
    )
    return MetaRegressionResult(
        intercept=intercept,
        coef=coef,
        se=se,
        p=p,
        r2=r2,
        n=len(effects),
        bubble_plot_png=png,
    )


__all__ = ["MetaRegressionResult", "meta_regression"]
