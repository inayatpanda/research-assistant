"""Stats chart renderers — Phase 8.5.

Pure-function chart renderers + dispatcher. Every renderer returns the dict
shape stored in AnalysisResult.chart:
  {"format": "png", "data_uri": "data:image/png;base64,...", "byte_size": N}
"""
from __future__ import annotations

import logging
from typing import Any, Callable

import pandas as pd

from .box_plot import render_box_plot
from .histogram import render_categorical_counts, render_histogram
from .km_curve import render_km_curve
from .qq_plot import render_qq_plot
from .scatter_plot import render_scatter_plot

log = logging.getLogger(__name__)

__all__ = [
    "render_box_plot",
    "render_histogram",
    "render_categorical_counts",
    "render_qq_plot",
    "render_scatter_plot",
    "render_km_curve",
    "select_and_render",
]


def _pre_post_diff_long(df: pd.DataFrame, pre: str, post: str) -> pd.DataFrame:
    """Return a frame with a single column 'diff' = post - pre, NaN-dropped."""
    sub = df[[pre, post]].dropna()
    diff = sub[post].to_numpy(dtype=float) - sub[pre].to_numpy(dtype=float)
    return pd.DataFrame({"diff": diff})


def _long_form_rm(
    df: pd.DataFrame, subject: str, within: str, outcome: str
) -> pd.DataFrame:
    """Long-form table for rm_anova box plot: time × value × subject."""
    sub = df[[subject, within, outcome]].dropna()
    return sub.rename(columns={within: "time", outcome: "value"})


def _first_predictor(variables: dict[str, Any]) -> str:
    predictors = variables.get("predictors")
    if isinstance(predictors, list) and predictors:
        return predictors[0]
    if isinstance(predictors, str):
        return predictors
    predictor = variables.get("predictor")
    if isinstance(predictor, str):
        return predictor
    raise ValueError("no predictor or predictors specified")


def _km_groups(variables: dict[str, Any]) -> str | None:
    g = variables.get("groups")
    if isinstance(g, str):
        return g
    return None


def _cox_first_covariate(variables: dict[str, Any]) -> str | None:
    covs = variables.get("covariates")
    if isinstance(covs, list) and covs:
        return covs[0]
    if isinstance(covs, str):
        return covs
    return None


# Maps test_key -> renderer-callable(df, variables) -> chart dict, or None.
_CHART_BY_TEST: dict[
    str, Callable[[pd.DataFrame, dict[str, Any]], dict[str, Any]] | None
] = {
    "independent_t": lambda df, v: render_box_plot(
        df=df, outcome=v["outcome"], groups=v["groups"]
    ),
    "paired_t": lambda df, v: render_histogram(
        df=_pre_post_diff_long(df, v["pre"], v["post"]), column="diff", kde=True
    ),
    "mann_whitney": lambda df, v: render_box_plot(
        df=df, outcome=v["outcome"], groups=v["groups"]
    ),
    "wilcoxon_signed": lambda df, v: render_histogram(
        df=_pre_post_diff_long(df, v["pre"], v["post"]), column="diff", kde=True
    ),
    "chi_squared": lambda df, v: render_categorical_counts(
        df=df, var_a=v["outcome"], var_b=v["groups"]
    ),
    "fisher_exact": lambda df, v: render_categorical_counts(
        df=df, var_a=v["outcome"], var_b=v["groups"]
    ),
    "one_way_anova": lambda df, v: render_box_plot(
        df=df, outcome=v["outcome"], groups=v["groups"]
    ),
    "kruskal_wallis": lambda df, v: render_box_plot(
        df=df, outcome=v["outcome"], groups=v["groups"]
    ),
    "rm_anova": lambda df, v: render_box_plot(
        df=_long_form_rm(df, v["subject"], v["within"], v["outcome"]),
        outcome="value",
        groups="time",
    ),
    "pearson": lambda df, v: render_scatter_plot(
        df=df, x=v["x"], y=v["y"], fit="linear"
    ),
    "spearman": lambda df, v: render_scatter_plot(
        df=df, x=v["x"], y=v["y"], fit="lowess"
    ),
    "linear_regression": lambda df, v: render_scatter_plot(
        df=df, x=_first_predictor(v), y=v["outcome"], fit="linear"
    ),
    "multiple_linear": lambda df, v: render_scatter_plot(
        df=df, x=_first_predictor(v), y=v["outcome"], fit="linear"
    ),
    "logistic": lambda df, v: render_scatter_plot(
        df=df, x=_first_predictor(v), y=v["outcome"], fit="linear"
    ),
    "kaplan_meier": lambda df, v: render_km_curve(
        df=df, duration=v["time"], event=v["event"], groups=_km_groups(v)
    ),
    "cox_ph": lambda df, v: render_km_curve(
        df=df,
        duration=v["time"],
        event=v["event"],
        groups=_cox_first_covariate(v),
    ),
    # icc / cohen_kappa: small categorical agreement tables — no v1 chart.
    "icc": None,
    "cohen_kappa": None,
}


def select_and_render(
    *, test_key: str, df: pd.DataFrame, variables: dict[str, Any]
) -> dict[str, Any] | None:
    """Dispatch a chart render for the given test_key. On any failure, log a
    WARNING and return None — never raise. None is also returned when no chart
    applies to this test_key.
    """
    spec = _CHART_BY_TEST.get(test_key)
    if spec is None:
        return None
    try:
        return spec(df, variables)
    except Exception as exc:
        log.warning("Chart render failed for %s: %s", test_key, exc)
        return None
