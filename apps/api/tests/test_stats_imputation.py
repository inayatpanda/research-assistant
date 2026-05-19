"""Phase 17 (MP17) — Imputation + Rubin's-rule pooling tests."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from research_api.services.stats.imputation import (
    PooledSummary,
    impute_simple,
    pool_with_rubin,
    run_mice,
)


def _make_df_with_missing(seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n = 80
    x = rng.normal(5.0, 2.0, n)
    y = 2.0 + 0.5 * x + rng.normal(0, 0.5, n)
    # Inject ~15% MCAR missing into y.
    miss_mask = rng.random(n) < 0.15
    y_with_miss = y.copy()
    y_with_miss[miss_mask] = np.nan
    return pd.DataFrame({"x": x, "y": y_with_miss})


# ── MICE + Rubin's rules ────────────────────────────────────────────────────


def test_run_mice_returns_five_complete_frames_by_default():
    df = _make_df_with_missing()
    imputed = run_mice(df, target_cols=["y"], n_imputations=5, seed=42)
    assert len(imputed) == 5
    for f in imputed:
        assert f["y"].isna().sum() == 0


def test_pool_with_rubin_recovers_mean_close_to_truth():
    df = _make_df_with_missing()
    imputed = run_mice(df, target_cols=["y"], n_imputations=5, seed=42)
    pooled = pool_with_rubin(imputed, target_cols=["y"])
    assert len(pooled) == 1
    p = pooled[0]
    # The truth-data mean of `y` ≈ 4.5; pooled estimate should be close.
    obs_mean = float(df["y"].dropna().mean())
    assert math.isclose(p.q_bar, obs_mean, abs_tol=0.5)
    # Total variance must be >= within-imputation variance.
    assert p.total_var >= p.u_bar - 1e-10


def test_rubin_pooled_total_variance_formula():
    """T = U + (1+1/m)*B by construction."""
    df = _make_df_with_missing(seed=3)
    imputed = run_mice(df, target_cols=["y"], n_imputations=5, seed=7)
    pooled = pool_with_rubin(imputed, target_cols=["y"])
    p = pooled[0]
    expected_total = p.u_bar + (1 + 1.0 / 5) * p.between_var
    assert math.isclose(p.total_var, expected_total, rel_tol=1e-9)


def test_pool_with_rubin_skips_non_numeric_columns():
    frames = [
        pd.DataFrame({"y": [1.0, 2.0, 3.0], "label": ["a", "b", "c"]})
    ]
    pooled = pool_with_rubin(frames, target_cols=["y", "label"])
    assert len(pooled) == 1
    assert pooled[0].column == "y"


def test_run_mice_rejects_zero_imputations():
    df = _make_df_with_missing()
    with pytest.raises(ValueError):
        run_mice(df, target_cols=["y"], n_imputations=0)


def test_run_mice_requires_numeric_target():
    df = pd.DataFrame({"label": ["a", "b", "c"]})
    with pytest.raises(ValueError):
        run_mice(df, target_cols=["label"], n_imputations=2)


def test_pool_with_rubin_single_imputation_treats_between_as_zero():
    """m=1 → between-variance is 0; pooled SE comes entirely from within."""
    df = _make_df_with_missing()
    imputed = run_mice(df, target_cols=["y"], n_imputations=1, seed=7)
    pooled = pool_with_rubin(imputed, target_cols=["y"])
    assert pooled[0].between_var == 0.0


# ── Simple fallbacks ────────────────────────────────────────────────────────


def test_impute_simple_mean_fills_missing_with_column_mean():
    df = pd.DataFrame({"x": [1.0, 2.0, np.nan, 4.0]})
    out = impute_simple(df, method="mean", target_cols=["x"])
    assert math.isclose(out.loc[2, "x"], (1.0 + 2.0 + 4.0) / 3, abs_tol=1e-9)


def test_impute_simple_median_fills_missing_with_column_median():
    df = pd.DataFrame({"x": [1.0, 2.0, np.nan, 3.0, 100.0]})
    out = impute_simple(df, method="median", target_cols=["x"])
    assert math.isclose(out.loc[2, "x"], 2.5, abs_tol=1e-9)


def test_impute_simple_last_observation_carries_forward():
    df = pd.DataFrame({"x": [1.0, np.nan, np.nan, 4.0]})
    out = impute_simple(df, method="last_observation", target_cols=["x"])
    assert out["x"].tolist() == [1.0, 1.0, 1.0, 4.0]


def test_impute_simple_knn_fills_numeric_target():
    df = pd.DataFrame({"x": [1.0, 2.0, np.nan, 4.0, 5.0], "y": [10.0, 20.0, 30.0, 40.0, 50.0]})
    out = impute_simple(df, method="knn", target_cols=["x"])
    assert not out["x"].isna().any()


def test_impute_simple_rejects_unknown_method():
    df = pd.DataFrame({"x": [1.0, 2.0]})
    with pytest.raises(ValueError):
        impute_simple(df, method="bogus", target_cols=["x"])
