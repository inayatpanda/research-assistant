from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from research_api.services.stats.runner import TestResult, run


def test_independent_t_known_answer():
    df = pd.DataFrame(
        {
            "score": [10, 12, 14, 11, 13, 9, 9, 8, 7, 10, 6, 8],
            "group": ["A"] * 6 + ["B"] * 6,
        }
    )
    out = run(test_key="independent_t", df=df, variables={"outcome": "score", "groups": "group"})
    assert isinstance(out, TestResult)
    assert out.test_key == "independent_t"
    assert out.n == 12
    assert out.statistic == pytest.approx(3.6556, rel=1e-3)
    assert out.p_value == pytest.approx(0.004420919566981322, rel=1e-3)
    assert out.effect_size == pytest.approx(2.1106, rel=1e-2)
    assert out.df == pytest.approx(10.0, abs=1e-6)
    assert out.ci_low is not None
    assert out.ci_high is not None
    assert out.ci_low < out.ci_high


def test_paired_t_known_answer():
    df = pd.DataFrame({"pre": [1.0, 2, 3, 4, 5, 6], "post": [2.0, 3.5, 4, 5, 6.5, 8]})
    out = run(
        test_key="paired_t",
        df=df,
        variables={"pre": "pre", "post": "post"},
    )
    assert out.n == 6
    assert out.statistic == pytest.approx(-8.0, rel=1e-3)
    assert out.p_value == pytest.approx(0.0004929066605724442, rel=1e-3)
    assert out.effect_size == pytest.approx(3.2660, rel=1e-2)


def test_mann_whitney_known_answer():
    df = pd.DataFrame(
        {
            "x": [5, 6, 7, 8, 9, 1, 2, 3, 4, 5],
            "g": ["A"] * 5 + ["B"] * 5,
        }
    )
    out = run(
        test_key="mann_whitney",
        df=df,
        variables={"outcome": "x", "groups": "g"},
    )
    assert out.n == 10
    assert out.statistic == pytest.approx(24.5, rel=1e-3)
    assert out.p_value == pytest.approx(0.01597, abs=1e-3)
    assert out.effect_size is not None


def test_wilcoxon_signed_known_answer():
    df = pd.DataFrame(
        {
            "pre": [10, 11, 12, 13, 14, 15],
            "post": [12, 13, 15, 14, 16, 18],
        }
    )
    out = run(
        test_key="wilcoxon_signed",
        df=df,
        variables={"pre": "pre", "post": "post"},
    )
    assert out.n == 6
    assert out.statistic == pytest.approx(0.0, abs=1e-6)
    assert out.p_value == pytest.approx(0.03125, rel=1e-3)


def test_chi_squared_known_answer():
    df = pd.DataFrame(
        {
            "outcome": (["yes"] * 10 + ["no"] * 20) + (["yes"] * 20 + ["no"] * 10),
            "group": ["A"] * 30 + ["B"] * 30,
        }
    )
    out = run(
        test_key="chi_squared",
        df=df,
        variables={"outcome": "outcome", "groups": "group"},
    )
    assert out.n == 60
    assert out.statistic == pytest.approx(6.6667, rel=1e-3)
    assert out.p_value == pytest.approx(0.009823, rel=1e-3)
    assert out.df == pytest.approx(1.0, abs=1e-6)
    assert out.effect_size == pytest.approx(0.3333, rel=1e-2)


def test_fisher_exact_known_answer():
    df = pd.DataFrame(
        {
            "outcome": (["yes"] * 8 + ["no"] * 2) + (["yes"] * 1 + ["no"] * 5),
            "group": ["A"] * 10 + ["B"] * 6,
        }
    )
    out = run(
        test_key="fisher_exact",
        df=df,
        variables={"outcome": "outcome", "groups": "group"},
    )
    assert out.n == 16
    or_value = out.statistic
    assert or_value == pytest.approx(0.05, rel=1e-3) or or_value == pytest.approx(20.0, rel=1e-3)
    assert out.p_value == pytest.approx(0.034965, rel=1e-3)


def test_one_way_anova_known_answer():
    df = pd.DataFrame(
        {
            "y": [1, 2, 3, 4, 5, 2, 3, 4, 5, 6, 5, 6, 7, 8, 9],
            "g": ["A"] * 5 + ["B"] * 5 + ["C"] * 5,
        }
    )
    out = run(
        test_key="one_way_anova",
        df=df,
        variables={"outcome": "y", "groups": "g"},
    )
    assert out.n == 15
    assert out.statistic == pytest.approx(8.6667, rel=1e-3)
    assert out.p_value == pytest.approx(0.004687, rel=1e-3)
    assert out.effect_size is not None


def test_kruskal_wallis_known_answer():
    df = pd.DataFrame(
        {
            "y": [1, 2, 3, 4, 5, 2, 3, 4, 5, 6, 5, 6, 7, 8, 9],
            "g": ["A"] * 5 + ["B"] * 5 + ["C"] * 5,
        }
    )
    out = run(
        test_key="kruskal_wallis",
        df=df,
        variables={"outcome": "y", "groups": "g"},
    )
    assert out.n == 15
    assert out.statistic == pytest.approx(8.263, rel=1e-3)
    assert out.p_value == pytest.approx(0.01606, rel=1e-3)


def test_rm_anova_known_answer():
    df = pd.DataFrame(
        {
            "subject": [1, 2, 3, 4, 1, 2, 3, 4, 1, 2, 3, 4],
            "time": ["t1"] * 4 + ["t2"] * 4 + ["t3"] * 4,
            "score": [10, 12, 14, 11, 12, 15, 16, 13, 15, 18, 19, 17],
        }
    )
    out = run(
        test_key="rm_anova",
        df=df,
        variables={"outcome": "score", "within": "time", "subject": "subject"},
    )
    assert out.statistic == pytest.approx(220.2, rel=1e-2)
    assert out.p_value < 0.001


def test_pearson_known_answer():
    df = pd.DataFrame(
        {
            "x": [1, 2, 3, 4, 5, 6, 7],
            "y": [2, 4, 5, 4, 5, 7, 8],
        }
    )
    out = run(test_key="pearson", df=df, variables={"x": "x", "y": "y"})
    assert out.n == 7
    assert out.statistic == pytest.approx(0.92582, rel=1e-3)
    assert out.p_value == pytest.approx(0.002765, rel=1e-3)
    assert out.ci_low is not None and out.ci_high is not None


def test_spearman_known_answer():
    df = pd.DataFrame(
        {
            "x": [1, 2, 3, 4, 5, 6, 7],
            "y": [2, 4, 5, 4, 5, 7, 8],
        }
    )
    out = run(test_key="spearman", df=df, variables={"x": "x", "y": "y"})
    assert out.n == 7
    assert out.statistic == pytest.approx(0.9092, rel=1e-3)
    assert out.p_value == pytest.approx(0.004537, rel=1e-3)


def test_linear_regression_known_answer():
    df = pd.DataFrame(
        {
            "x": [1, 2, 3, 4, 5, 6, 7],
            "y": [2, 4, 5, 4, 5, 7, 8],
        }
    )
    out = run(
        test_key="linear_regression",
        df=df,
        variables={"outcome": "y", "predictors": ["x"]},
    )
    assert out.n == 7
    assert out.extras["coef_x"] == pytest.approx(0.85714, rel=1e-3)
    assert out.extras["r_squared"] == pytest.approx(0.8571, rel=1e-3)
    assert out.p_value == pytest.approx(0.0027649603013049596, rel=1e-3)


def test_multiple_linear_known_answer():
    df = pd.DataFrame(
        {
            "x1": [1, 2, 3, 4, 5, 6, 7, 8],
            "x2": [2, 3, 2, 5, 4, 6, 5, 8],
            "y": [3, 5, 5, 8, 8, 11, 11, 14],
        }
    )
    out = run(
        test_key="multiple_linear",
        df=df,
        variables={"outcome": "y", "predictors": ["x1", "x2"]},
    )
    assert out.n == 8
    assert out.statistic == pytest.approx(932.4149816176425, rel=1e-3)
    assert out.p_value == pytest.approx(3.6976e-07, rel=1e-2)
    assert out.extras["r_squared"] == pytest.approx(0.9973, rel=1e-3)


def test_logistic_known_answer():
    df = pd.DataFrame(
        {
            "x": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            "y": [0, 0, 0, 0, 1, 0, 1, 1, 1, 1],
        }
    )
    out = run(
        test_key="logistic",
        df=df,
        variables={"outcome": "y", "predictors": ["x"]},
    )
    assert out.n == 10
    assert out.extras["coef_x"] == pytest.approx(1.30164, rel=1e-3)
    assert out.extras["or_x"] == pytest.approx(3.6753, rel=1e-3)


def test_kaplan_meier_known_answer():
    df = pd.DataFrame(
        {
            "time": [5, 6, 6, 2.5, 4, 4, 3, 2, 4, 3, 2, 1],
            "event": [1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
            "group": ["A"] * 6 + ["B"] * 6,
        }
    )
    out = run(
        test_key="kaplan_meier",
        df=df,
        variables={"time": "time", "event": "event", "groups": "group"},
    )
    assert out.n == 12
    assert out.statistic == pytest.approx(5.7604, rel=1e-2)
    assert out.p_value == pytest.approx(0.01639, rel=1e-2)
    assert out.chart is not None
    # Phase 8.5: chart is a server-rendered PNG data URI dict; older 'type'/
    # 'series' shape was superseded by the chart dispatcher.
    assert out.chart["format"] == "png"
    assert out.chart["data_uri"].startswith("data:image/png;base64,")


def test_cox_ph_known_answer():
    rng = np.random.default_rng(7)
    n = 40
    df = pd.DataFrame(
        {
            "time": rng.uniform(1, 50, size=n),
            "event": rng.integers(0, 2, size=n),
            "age": rng.normal(50, 10, size=n),
        }
    )
    out = run(
        test_key="cox_ph",
        df=df,
        variables={"time": "time", "event": "event", "covariates": ["age"]},
    )
    assert out.n == 40
    assert out.extras["hr_age"] == pytest.approx(0.9571, rel=1e-2)
    assert out.p_value == pytest.approx(0.17035, rel=1e-2)


def test_icc_known_answer():
    df = pd.DataFrame(
        {
            "subj": [1, 2, 3, 4, 5, 6, 1, 2, 3, 4, 5, 6],
            "rater": ["A"] * 6 + ["B"] * 6,
            "score": [5, 6, 7, 8, 9, 10, 5, 7, 7, 9, 9, 10],
        }
    )
    out = run(
        test_key="icc",
        df=df,
        variables={"subject": "subj", "rater": "rater", "rating": "score"},
    )
    assert out.statistic == pytest.approx(0.9517, rel=1e-2)
    assert out.p_value < 0.001


def test_cohen_kappa_known_answer():
    df = pd.DataFrame(
        {
            "a": ["a", "a", "b", "b", "a", "b"],
            "b": ["a", "b", "b", "b", "a", "a"],
        }
    )
    out = run(
        test_key="cohen_kappa",
        df=df,
        variables={"rater_a": "a", "rater_b": "b"},
    )
    assert out.n == 6
    assert out.statistic == pytest.approx(0.3333, rel=1e-2)


def test_run_unknown_test_key_raises():
    df = pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})
    with pytest.raises(ValueError, match="unknown test_key"):
        run(test_key="bogus", df=df, variables={"x": "x", "y": "y"})


def test_run_missing_column_raises():
    df = pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})
    with pytest.raises(ValueError, match="column"):
        run(
            test_key="independent_t",
            df=df,
            variables={"outcome": "score_missing", "groups": "y"},
        )


def test_run_rejects_non_whitelisted_column_name():
    df = pd.DataFrame({"x; DROP TABLE": [1, 2, 3], "g": ["A", "B", "A"]})
    with pytest.raises(ValueError, match="invalid column name"):
        run(
            test_key="independent_t",
            df=df,
            variables={"outcome": "x; DROP TABLE", "groups": "g"},
        )


def test_run_drops_rows_with_nan_in_required_cols():
    df = pd.DataFrame(
        {
            "y": [1.0, 2.0, np.nan, 4.0, 5.0, 6.0, np.nan, 8.0],
            "g": ["A", "A", "A", "A", "B", "B", "B", "B"],
        }
    )
    out = run(
        test_key="independent_t",
        df=df,
        variables={"outcome": "y", "groups": "g"},
    )
    assert out.n == 6


def test_run_invalid_variables_payload_raises():
    df = pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})
    with pytest.raises(ValueError):
        run(test_key="independent_t", df=df, variables={"outcome": "x"})
