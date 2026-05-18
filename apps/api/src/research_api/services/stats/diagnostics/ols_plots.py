"""Phase 13 — Four-panel OLS diagnostic plots.

Generates the classic R-style regression diagnostics:

  1. residuals_vs_fitted: residuals vs fitted values (linearity / spread).
  2. qq: normal Q-Q plot of standardised residuals.
  3. scale_location: sqrt(|standardised residuals|) vs fitted values.
  4. residuals_vs_leverage: standardised residuals vs leverage, with Cook's
     distance contours implied via the dot-size encoding.

Each returns PNG bytes; the caller serialises to a base64 data URI for the
``AnalysisResult.chart`` JSON column.
"""
from __future__ import annotations

import math
from io import BytesIO
from typing import Any

import matplotlib

matplotlib.use("Agg")  # MUST come before pyplot import.
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats as sp_stats  # noqa: E402

_DPI = 130
_FIGSIZE = (6.0, 4.0)


def _fig_to_png(fig: Any) -> bytes:
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=_DPI, bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


def _residuals_vs_fitted(fitted: np.ndarray, resid: np.ndarray) -> bytes:
    fig = plt.figure(figsize=_FIGSIZE, dpi=_DPI)
    ax = fig.add_subplot(1, 1, 1)
    ax.scatter(fitted, resid, alpha=0.6, color="#3b82f6", edgecolor="white", linewidth=0.5)
    ax.axhline(0.0, color="#9ca3af", linestyle="--", linewidth=1)
    # Lowess-ish smoothing via numpy polyfit of degree 2 for a quick trend hint.
    if len(fitted) >= 5 and np.std(fitted) > 0:
        order = np.argsort(fitted)
        try:
            poly = np.polyfit(fitted, resid, 2)
            xs = np.linspace(fitted.min(), fitted.max(), 100)
            ys = np.polyval(poly, xs)
            ax.plot(xs, ys, color="#ef4444", linewidth=1.5)
        except (np.linalg.LinAlgError, ValueError):
            _ = order
    ax.set_xlabel("Fitted values")
    ax.set_ylabel("Residuals")
    ax.set_title("Residuals vs Fitted")
    ax.grid(True, alpha=0.3)
    return _fig_to_png(fig)


def _qq_plot(std_resid: np.ndarray) -> bytes:
    fig = plt.figure(figsize=_FIGSIZE, dpi=_DPI)
    ax = fig.add_subplot(1, 1, 1)
    sp_stats.probplot(std_resid, dist="norm", plot=ax)
    lines = ax.get_lines()
    if len(lines) >= 2:
        lines[0].set_markerfacecolor("#3b82f6")
        lines[0].set_markeredgecolor("#3b82f6")
        lines[1].set_color("#ef4444")
    ax.set_xlabel("Theoretical quantiles")
    ax.set_ylabel("Standardised residuals")
    ax.set_title("Normal Q-Q")
    ax.grid(True, alpha=0.3)
    return _fig_to_png(fig)


def _scale_location(fitted: np.ndarray, std_resid: np.ndarray) -> bytes:
    fig = plt.figure(figsize=_FIGSIZE, dpi=_DPI)
    ax = fig.add_subplot(1, 1, 1)
    sqrt_abs = np.sqrt(np.abs(std_resid))
    ax.scatter(fitted, sqrt_abs, alpha=0.6, color="#3b82f6", edgecolor="white", linewidth=0.5)
    if len(fitted) >= 5 and np.std(fitted) > 0:
        try:
            poly = np.polyfit(fitted, sqrt_abs, 2)
            xs = np.linspace(fitted.min(), fitted.max(), 100)
            ys = np.polyval(poly, xs)
            ax.plot(xs, ys, color="#ef4444", linewidth=1.5)
        except (np.linalg.LinAlgError, ValueError):
            pass
    ax.set_xlabel("Fitted values")
    ax.set_ylabel("Sqrt |Standardised residuals|")
    ax.set_title("Scale-Location")
    ax.grid(True, alpha=0.3)
    return _fig_to_png(fig)


def _residuals_vs_leverage(leverage: np.ndarray, std_resid: np.ndarray, cooks: np.ndarray) -> bytes:
    fig = plt.figure(figsize=_FIGSIZE, dpi=_DPI)
    ax = fig.add_subplot(1, 1, 1)
    sizes = 20 + 200 * (cooks / max(cooks.max(), 1e-9))
    ax.scatter(
        leverage,
        std_resid,
        s=sizes,
        alpha=0.5,
        color="#3b82f6",
        edgecolor="white",
        linewidth=0.5,
    )
    ax.axhline(0.0, color="#9ca3af", linestyle="--", linewidth=1)
    ax.set_xlabel("Leverage")
    ax.set_ylabel("Standardised residuals")
    ax.set_title("Residuals vs Leverage (dot size = Cook's D)")
    ax.grid(True, alpha=0.3)
    return _fig_to_png(fig)


def ols_diagnostic_plots(
    df: pd.DataFrame,
    outcome: str,
    predictors: list[str],
) -> dict[str, bytes]:
    """Fit OLS via statsmodels and return the four diagnostic PNGs.

    Raises ``ValueError`` if the formula cannot be fit (e.g. insufficient
    rows after NaN drop, singular design matrix).
    """
    import statsmodels.formula.api as smf

    if outcome not in df.columns:
        raise ValueError(f"outcome {outcome!r} not in dataframe")
    for p in predictors:
        if p not in df.columns:
            raise ValueError(f"predictor {p!r} not in dataframe")
    sub = df[[outcome, *predictors]].dropna()
    if len(sub) < max(5, len(predictors) + 2):
        raise ValueError("not enough rows to fit OLS diagnostics")

    formula = f"{outcome} ~ " + " + ".join(predictors)
    model = smf.ols(formula, data=sub).fit()
    fitted = np.asarray(model.fittedvalues, dtype=float)
    resid = np.asarray(model.resid, dtype=float)
    influence = model.get_influence()
    std_resid = np.asarray(influence.resid_studentized_internal, dtype=float)
    leverage = np.asarray(influence.hat_matrix_diag, dtype=float)
    cooks_d = np.asarray(influence.cooks_distance[0], dtype=float)
    # Defensive: replace inf/nan so plotters don't fail.
    std_resid = np.where(np.isfinite(std_resid), std_resid, 0.0)
    leverage = np.where(np.isfinite(leverage), leverage, 0.0)
    cooks_d = np.where(np.isfinite(cooks_d), cooks_d, 0.0)

    return {
        "residuals_vs_fitted": _residuals_vs_fitted(fitted, resid),
        "qq": _qq_plot(std_resid),
        "scale_location": _scale_location(fitted, std_resid),
        "residuals_vs_leverage": _residuals_vs_leverage(leverage, std_resid, cooks_d),
    }


# Unused-import guard for environments that strip math.
_ = math
