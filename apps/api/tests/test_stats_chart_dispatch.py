"""Tests for the runner → chart dispatcher wire-up — Phase 8.5 Task 7."""
from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd
import pytest

from research_api.services.stats import charts as charts_pkg
from research_api.services.stats.charts import (
    _long_form_rm,
    _pre_post_diff_long,
    select_and_render,
)
from research_api.services.stats.runner import run


# ---- Fixtures keyed by test_key --------------------------------------------


def _two_group_df(n: int = 30, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame(
        {
            "y": np.concatenate([rng.normal(0, 1, n), rng.normal(1, 1, n)]),
            "g": ["A"] * n + ["B"] * n,
        }
    )


def _pre_post_df(n: int = 30, seed: int = 1) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame(
        {
            "pre": rng.normal(0, 1, n),
            "post": rng.normal(0.4, 1, n),
        }
    )


def _three_group_df(n: int = 20, seed: int = 2) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame(
        {
            "y": np.concatenate(
                [rng.normal(0, 1, n), rng.normal(1, 1, n), rng.normal(2, 1, n)]
            ),
            "g": ["A"] * n + ["B"] * n + ["C"] * n,
        }
    )


def _two_by_two_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "outcome": ["yes", "no", "yes", "no"] * 12,
            "groups": ["A", "A", "B", "B"] * 12,
        }
    )


def _rm_df() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    rng = np.random.default_rng(3)
    for subj in range(12):
        for time in ["t1", "t2", "t3"]:
            rows.append(
                {"subj": subj, "time": time, "y": float(rng.normal(0, 1))}
            )
    return pd.DataFrame(rows)


def _xy_df(n: int = 60, seed: int = 4) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    x = rng.normal(0, 1, n)
    return pd.DataFrame({"x": x, "y": 2 * x + rng.normal(0, 0.5, n)})


def _ols_df(n: int = 50, seed: int = 5) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    x1 = rng.normal(0, 1, n)
    x2 = rng.normal(0, 1, n)
    y = 1.0 + 0.6 * x1 - 0.3 * x2 + rng.normal(0, 0.4, n)
    return pd.DataFrame({"y": y, "x1": x1, "x2": x2})


def _logit_df(n: int = 80, seed: int = 6) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    x = rng.normal(0, 1, n)
    p = 1.0 / (1.0 + np.exp(-(0.7 * x)))
    y = (rng.uniform(0, 1, n) < p).astype(int)
    return pd.DataFrame({"y": y, "x": x})


def _surv_df(n: int = 30, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame(
        {
            "time": rng.uniform(1, 30, n),
            "event": rng.integers(0, 2, n),
            "group": (["A"] * (n // 2)) + (["B"] * (n - n // 2)),
            "age": rng.normal(50, 8, n),
        }
    )


def _icc_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "subj": list(range(1, 7)) * 2,
            "rater": ["A"] * 6 + ["B"] * 6,
            "rating": [5, 6, 7, 8, 9, 10, 5, 7, 7, 9, 9, 10],
        }
    )


def _kappa_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "r1": ["yes", "yes", "no", "no", "yes", "no", "yes", "yes"],
            "r2": ["yes", "no", "no", "yes", "yes", "no", "no", "yes"],
        }
    )


_CASES: dict[str, tuple[pd.DataFrame, dict[str, Any]]] = {
    "independent_t": (_two_group_df(), {"outcome": "y", "groups": "g"}),
    "paired_t": (_pre_post_df(), {"pre": "pre", "post": "post"}),
    "mann_whitney": (_two_group_df(), {"outcome": "y", "groups": "g"}),
    "wilcoxon_signed": (_pre_post_df(), {"pre": "pre", "post": "post"}),
    "chi_squared": (_two_by_two_df(), {"outcome": "outcome", "groups": "groups"}),
    "fisher_exact": (_two_by_two_df(), {"outcome": "outcome", "groups": "groups"}),
    "one_way_anova": (_three_group_df(), {"outcome": "y", "groups": "g"}),
    "kruskal_wallis": (_three_group_df(), {"outcome": "y", "groups": "g"}),
    "rm_anova": (
        _rm_df(),
        {"subject": "subj", "within": "time", "outcome": "y"},
    ),
    "pearson": (_xy_df(), {"x": "x", "y": "y"}),
    "spearman": (_xy_df(), {"x": "x", "y": "y"}),
    "linear_regression": (_ols_df(), {"outcome": "y", "predictors": ["x1"]}),
    "multiple_linear": (
        _ols_df(),
        {"outcome": "y", "predictors": ["x1", "x2"]},
    ),
    "logistic": (_logit_df(), {"outcome": "y", "predictors": ["x"]}),
    "kaplan_meier": (
        _surv_df(),
        {"time": "time", "event": "event", "groups": "group"},
    ),
    "cox_ph": (
        _surv_df(),
        {"time": "time", "event": "event", "covariates": ["age"]},
    ),
    "icc": (_icc_df(), {"subject": "subj", "rater": "rater", "rating": "rating"}),
    "cohen_kappa": (_kappa_df(), {"rater_a": "r1", "rater_b": "r2"}),
}


_TESTS_WITHOUT_CHART = {"icc", "cohen_kappa"}


# ---- Tests ------------------------------------------------------------------


_OLS_TESTS_WITH_PANELS = {"linear_regression", "multiple_linear"}


@pytest.mark.parametrize("test_key", list(_CASES.keys()))
def test_runner_dispatch_produces_chart_or_none(test_key: str) -> None:
    df, variables = _CASES[test_key]
    result = run(test_key=test_key, df=df, variables=variables)
    if test_key in _TESTS_WITHOUT_CHART:
        assert result.chart is None
    else:
        assert isinstance(result.chart, dict)
        expected_keys = {"format", "data_uri", "byte_size"}
        if test_key in _OLS_TESTS_WITH_PANELS:
            # Phase 13 — OLS chart shape extends with a 4-panel diagnostic dict.
            expected_keys = expected_keys | {"panels"}
            panels = result.chart["panels"]
            assert isinstance(panels, dict)
            assert set(panels.keys()) == {
                "residuals_vs_fitted",
                "qq",
                "scale_location",
                "residuals_vs_leverage",
            }
            for v in panels.values():
                assert isinstance(v, str)
                assert v.startswith("data:image/png;base64,")
        assert set(result.chart.keys()) == expected_keys
        assert result.chart["format"] == "png"
        assert result.chart["data_uri"].startswith("data:image/png;base64,")


@pytest.mark.parametrize("test_key", list(_CASES.keys()))
def test_chart_dispatch_does_not_break_numerics(test_key: str) -> None:
    df, variables = _CASES[test_key]
    result = run(test_key=test_key, df=df, variables=variables)
    assert isinstance(result.statistic, float)
    assert isinstance(result.p_value, float) or result.p_value != result.p_value  # noqa: PLR0124


def test_chart_dispatch_failure_returns_none_not_raise(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(df: pd.DataFrame, v: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("simulated chart failure")

    monkeypatch.setitem(charts_pkg._CHART_BY_TEST, "independent_t", boom)
    df, variables = _CASES["independent_t"]
    result = run(test_key="independent_t", df=df, variables=variables)
    assert result.chart is None
    assert isinstance(result.statistic, float)


def test_chart_dispatch_logs_warning_on_failure(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def boom(df: pd.DataFrame, v: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("simulated chart failure XYZ")

    monkeypatch.setitem(charts_pkg._CHART_BY_TEST, "independent_t", boom)
    df, variables = _CASES["independent_t"]
    with caplog.at_level(logging.WARNING, logger="research_api.services.stats.charts"):
        run(test_key="independent_t", df=df, variables=variables)
    msgs = [r.getMessage() for r in caplog.records]
    assert any("Chart render failed for independent_t" in m for m in msgs)


def test_pre_post_diff_long_helper() -> None:
    df = pd.DataFrame({"a": [1.0, 2.0, 3.0], "b": [3.0, 5.0, 4.0]})
    out = _pre_post_diff_long(df, "a", "b")
    assert list(out.columns) == ["diff"]
    assert out["diff"].tolist() == [2.0, 3.0, 1.0]


def test_long_form_rm_helper() -> None:
    df = pd.DataFrame(
        {
            "subj": [1, 1, 2, 2],
            "t": ["pre", "post", "pre", "post"],
            "score": [10.0, 12.0, 9.0, 11.0],
        }
    )
    out = _long_form_rm(df, "subj", "t", "score")
    assert set(out.columns) == {"subj", "time", "value"}
    assert out["value"].tolist() == [10.0, 12.0, 9.0, 11.0]


def test_select_and_render_returns_none_for_unknown_test_key() -> None:
    df, variables = _CASES["independent_t"]
    assert select_and_render(test_key="not_a_real_test", df=df, variables=variables) is None
