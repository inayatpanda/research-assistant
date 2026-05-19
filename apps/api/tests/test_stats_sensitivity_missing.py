"""Phase 17 (MP17) — Missing-data sensitivity analysis tests."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from research_api.services.stats.sensitivity_missing import (
    best_case,
    tipping_point,
    worst_case,
)


def _df_with_missing(seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n = 60
    a = rng.normal(5.0, 1.0, n)
    b = rng.normal(3.0, 1.0, n)
    # Add 10 NaNs to arm A and 5 to arm B.
    a[:10] = np.nan
    b[:5] = np.nan
    return pd.DataFrame(
        {
            "y": np.concatenate([a, b]),
            "group": ["A"] * n + ["B"] * n,
        }
    )


# ── Worst / best case ───────────────────────────────────────────────────────


def test_worst_case_returns_effect_estimate_and_p_value():
    df = _df_with_missing()
    res = worst_case(df, outcome="y", group="group")
    assert res["type"] == "worst_case"
    assert res["effect_estimate"] is not None
    assert 0.0 <= res["p_value"] <= 1.0
    assert res["n_imputed"] == 15


def test_best_case_inflates_the_favoured_arm():
    df = _df_with_missing()
    worst = worst_case(df, outcome="y", group="group")
    best = best_case(df, outcome="y", group="group")
    # In higher_better mode, best-case fills A with the maximum and B with
    # the minimum, so the A-vs-B mean diff should be larger than worst-case.
    assert best["effect_estimate"] > worst["effect_estimate"]


def test_worst_case_rejects_three_groups():
    df = pd.DataFrame(
        {
            "y": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
            "group": ["A", "A", "B", "B", "C", "C"],
        }
    )
    with pytest.raises(ValueError, match="exactly 2 groups"):
        worst_case(df, outcome="y", group="group")


def test_worst_case_validates_direction():
    df = _df_with_missing()
    with pytest.raises(ValueError):
        worst_case(df, outcome="y", group="group", direction="upwards")


# ── Tipping point ──────────────────────────────────────────────────────────


def test_tipping_point_finds_flip_when_significance_can_change():
    """If observed A is much higher than B with a tight CI, but we fill enough
    missing A rows with low values, significance should flip — the tipping
    point search finds that threshold."""
    rng = np.random.default_rng(0)
    n = 30
    a = rng.normal(5.0, 0.5, n)
    b = rng.normal(0.0, 0.5, n)
    # 15 NaNs in A (half of arm).
    a[:15] = np.nan
    df = pd.DataFrame({"y": np.concatenate([a, b]), "group": ["A"] * n + ["B"] * n})
    res = tipping_point(
        df, outcome="y", group="group", candidate_low=-5.0, candidate_high=10.0
    )
    assert res["type"] == "tipping_point"
    assert res["threshold"] is not None
    assert -5.0 <= res["threshold"] <= 10.0


def test_tipping_point_returns_none_when_no_flip():
    """Two clearly separated arms with very few NaNs → significance survives all
    imputation values within the observed range."""
    rng = np.random.default_rng(7)
    n = 200
    a = rng.normal(10.0, 1.0, n)
    b = rng.normal(0.0, 1.0, n)
    a[0] = float("nan")  # 1 NaN
    df = pd.DataFrame({"y": np.concatenate([a, b]), "group": ["A"] * n + ["B"] * n})
    res = tipping_point(
        df, outcome="y", group="group", candidate_low=-1.0, candidate_high=11.0
    )
    assert res["threshold"] is None
    assert res["p_value"] is None


def test_tipping_point_validates_bracket():
    df = _df_with_missing()
    with pytest.raises(ValueError, match="< candidate_high"):
        tipping_point(
            df, outcome="y", group="group", candidate_low=5.0, candidate_high=5.0
        )
