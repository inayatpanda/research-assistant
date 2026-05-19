"""Phase 13 (MP13) — Known-answer tests for the extended catalogue.

Targets:
  - mixed_effects_lm
  - glm_poisson, glm_binomial, glm_gamma
  - gee
  - bootstrap_mean_diff
  - permutation_test
  - tost_equivalence, tost_noninferiority
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from research_api.services.stats.runner import run as runner_run


# ── helpers ─────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _seed_rng():
    np.random.seed(42)


def _longitudinal_df(seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for sid in range(30):
        intercept = rng.normal(0, 1.5)
        for t in range(4):
            y = 2.0 + 0.5 * t + intercept + rng.normal(0, 0.3)
            rows.append({"sid": f"s{sid}", "time": t, "y": y, "drug": t % 2})
    return pd.DataFrame(rows)


# ── mixed_effects_lm ────────────────────────────────────────────────────


def test_mixed_effects_lm_known_answer():
    df = _longitudinal_df()
    out = runner_run(
        test_key="mixed_effects_lm",
        df=df,
        variables={"outcome": "y", "predictors": ["time"], "cluster": "sid"},
    )
    # Slope on `time` should be ~0.5 (the true coefficient).
    assert math.isclose(out.extras["coef_time"], 0.5, abs_tol=0.1)
    assert out.extras["n_clusters"] == 30
    assert out.n == 120


def test_mixed_effects_lm_requires_cluster():
    df = _longitudinal_df()
    with pytest.raises(ValueError):
        runner_run(
            test_key="mixed_effects_lm",
            df=df,
            variables={"outcome": "y", "predictors": ["time"]},
        )


# ── glm_poisson ─────────────────────────────────────────────────────────


def test_glm_poisson_known_count_relationship():
    rng = np.random.default_rng(11)
    n = 200
    x = rng.normal(0, 1, n)
    lam = np.exp(0.5 + 0.3 * x)
    y = rng.poisson(lam)
    df = pd.DataFrame({"y": y, "x": x})
    out = runner_run(
        test_key="glm_poisson",
        df=df,
        variables={"outcome": "y", "predictors": ["x"]},
    )
    # Coefficient ~0.3.
    assert math.isclose(out.extras["coef_x"], 0.3, abs_tol=0.15)
    assert out.extras["family"] == "Poisson"


# ── glm_binomial ────────────────────────────────────────────────────────


def test_glm_binomial_recovers_log_odds():
    rng = np.random.default_rng(22)
    n = 400
    x = rng.normal(0, 1, n)
    logits = -0.5 + 1.0 * x
    p = 1 / (1 + np.exp(-logits))
    y = (rng.uniform(0, 1, n) < p).astype(int)
    df = pd.DataFrame({"y": y, "x": x})
    out = runner_run(
        test_key="glm_binomial",
        df=df,
        variables={"outcome": "y", "predictors": ["x"]},
    )
    assert math.isclose(out.extras["coef_x"], 1.0, abs_tol=0.3)
    assert out.extras["family"] == "Binomial"


# ── glm_gamma ───────────────────────────────────────────────────────────


def test_glm_gamma_strictly_positive_continuous():
    rng = np.random.default_rng(33)
    n = 250
    x = rng.normal(0, 1, n)
    mu = np.exp(1.0 + 0.2 * x)
    y = rng.gamma(shape=3.0, scale=mu / 3.0)
    df = pd.DataFrame({"y": y, "x": x})
    out = runner_run(
        test_key="glm_gamma",
        df=df,
        variables={"outcome": "y", "predictors": ["x"]},
    )
    assert math.isclose(out.extras["coef_x"], 0.2, abs_tol=0.2)
    assert out.extras["family"] == "Gamma"


# ── gee ─────────────────────────────────────────────────────────────────


def test_gee_known_repeated_measures():
    df = _longitudinal_df(seed=7)
    out = runner_run(
        test_key="gee",
        df=df,
        variables={"outcome": "y", "predictors": ["time"], "cluster": "sid"},
    )
    assert math.isclose(out.extras["coef_time"], 0.5, abs_tol=0.1)
    assert out.extras["cov_struct"] == "exchangeable"
    assert out.extras["n_clusters"] == 30


# ── bootstrap_mean_diff ────────────────────────────────────────────────


def test_bootstrap_mean_diff_known_answer():
    rng = np.random.default_rng(101)
    a = rng.normal(0, 1, 80)
    b = rng.normal(0.5, 1, 80)
    df = pd.DataFrame({"y": np.concatenate([a, b]), "g": ["a"] * 80 + ["b"] * 80})
    out = runner_run(
        test_key="bootstrap_mean_diff",
        df=df,
        variables={"outcome": "y", "groups": "g"},
    )
    # The observed diff should be ~0.5 (b - a).
    assert math.isclose(out.statistic, b.mean() - a.mean(), abs_tol=1e-9)
    # CI brackets the true 0.5 with very high probability.
    assert out.ci_low <= 0.5 <= out.ci_high
    assert out.extras["n_resamples"] == 9999
    assert len(out.extras["bootstrap_distribution"]) == 9999


# ── permutation_test ───────────────────────────────────────────────────


def test_permutation_test_rejects_strong_effect():
    rng = np.random.default_rng(202)
    a = rng.normal(0, 1, 60)
    b = rng.normal(2.0, 1, 60)
    df = pd.DataFrame({"y": np.concatenate([a, b]), "g": ["a"] * 60 + ["b"] * 60})
    out = runner_run(
        test_key="permutation_test",
        df=df,
        variables={"outcome": "y", "groups": "g"},
    )
    assert out.p_value < 0.001
    assert out.extras["n_resamples"] == 9999


def test_permutation_test_accepts_no_effect():
    rng = np.random.default_rng(303)
    a = rng.normal(0, 1, 60)
    b = rng.normal(0, 1, 60)
    df = pd.DataFrame({"y": np.concatenate([a, b]), "g": ["a"] * 60 + ["b"] * 60})
    out = runner_run(
        test_key="permutation_test",
        df=df,
        variables={"outcome": "y", "groups": "g"},
    )
    # Null is true — p > 0.05 most of the time. Loose threshold for stability.
    assert out.p_value > 0.05


# ── tost_equivalence / tost_noninferiority ─────────────────────────────


def test_tost_equivalence_rejects_within_bounds():
    rng = np.random.default_rng(404)
    # Two groups with means within ±0.5; equivalence margin (-1, +1).
    a = rng.normal(0.1, 0.5, 80)
    b = rng.normal(-0.1, 0.5, 80)
    df = pd.DataFrame({"y": np.concatenate([a, b]), "g": ["a"] * 80 + ["b"] * 80})
    out = runner_run(
        test_key="tost_equivalence",
        df=df,
        variables={
            "outcome": "y",
            "groups": "g",
            "low_eq": -1.0,
            "upp_eq": 1.0,
        },
    )
    assert out.p_value < 0.05  # equivalence proven
    assert out.extras["low_eq"] == -1.0
    assert out.extras["upp_eq"] == 1.0


def test_tost_equivalence_not_rejected_when_difference_outside_bounds():
    rng = np.random.default_rng(505)
    a = rng.normal(0, 1, 80)
    b = rng.normal(2.0, 1, 80)  # well outside +/- 1.0
    df = pd.DataFrame({"y": np.concatenate([a, b]), "g": ["a"] * 80 + ["b"] * 80})
    out = runner_run(
        test_key="tost_equivalence",
        df=df,
        variables={
            "outcome": "y",
            "groups": "g",
            "low_eq": -1.0,
            "upp_eq": 1.0,
        },
    )
    assert out.p_value > 0.05  # equivalence not proven


def test_tost_noninferiority_rejects_when_not_worse():
    rng = np.random.default_rng(606)
    # Group a is mean 0.2; comparator group b is mean 0.0; non-inferiority margin = -0.5.
    a = rng.normal(0.2, 1.0, 100)
    b = rng.normal(0.0, 1.0, 100)
    df = pd.DataFrame({"y": np.concatenate([a, b]), "g": ["a"] * 100 + ["b"] * 100})
    out = runner_run(
        test_key="tost_noninferiority",
        df=df,
        variables={
            "outcome": "y",
            "groups": "g",
            "low_eq": -0.5,
            "upp_eq": 5.0,
        },
    )
    # Non-inferiority must be demonstrated (p < 0.05).
    assert out.p_value < 0.05


def test_tost_requires_margins():
    df = pd.DataFrame({"y": [1.0, 2.0, 3.0, 4.0], "g": ["a", "a", "b", "b"]})
    with pytest.raises(ValueError):
        runner_run(
            test_key="tost_equivalence",
            df=df,
            variables={"outcome": "y", "groups": "g"},
        )


# ── catalogue presence guard ────────────────────────────────────────────


def test_new_test_keys_are_in_catalogue():
    from research_api.services.stats.registry import CATALOGUE

    for k in [
        "mixed_effects_lm",
        "glm_poisson",
        "glm_binomial",
        "glm_gamma",
        "gee",
        "bootstrap_mean_diff",
        "permutation_test",
        "tost_equivalence",
        "tost_noninferiority",
    ]:
        assert k in CATALOGUE
        assert CATALOGUE[k].key == k


# ── charts attach to result ─────────────────────────────────────────────


def test_bootstrap_attaches_distribution_chart():
    rng = np.random.default_rng(909)
    a = rng.normal(0, 1, 40)
    b = rng.normal(0.5, 1, 40)
    df = pd.DataFrame({"y": np.concatenate([a, b]), "g": ["a"] * 40 + ["b"] * 40})
    out = runner_run(
        test_key="bootstrap_mean_diff",
        df=df,
        variables={"outcome": "y", "groups": "g"},
    )
    assert out.chart is not None
    assert out.chart["format"] == "png"


def test_permutation_attaches_null_distribution_chart():
    rng = np.random.default_rng(910)
    a = rng.normal(0, 1, 40)
    b = rng.normal(0.5, 1, 40)
    df = pd.DataFrame({"y": np.concatenate([a, b]), "g": ["a"] * 40 + ["b"] * 40})
    out = runner_run(
        test_key="permutation_test",
        df=df,
        variables={"outcome": "y", "groups": "g"},
    )
    assert out.chart is not None
    assert out.chart["format"] == "png"


def test_tost_attaches_bounds_chart():
    rng = np.random.default_rng(911)
    a = rng.normal(0.1, 0.5, 60)
    b = rng.normal(-0.1, 0.5, 60)
    df = pd.DataFrame({"y": np.concatenate([a, b]), "g": ["a"] * 60 + ["b"] * 60})
    out = runner_run(
        test_key="tost_equivalence",
        df=df,
        variables={
            "outcome": "y",
            "groups": "g",
            "low_eq": -1.0,
            "upp_eq": 1.0,
        },
    )
    assert out.chart is not None
    assert out.chart["format"] == "png"
