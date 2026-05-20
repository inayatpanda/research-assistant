"""Phase 18 (MP18) — Bivariate cost-QALY bootstrap tests.

Synthetic two-arm trial data:
  - Intervention arm: cost ~ Normal(mu=1200, sd=50), qaly ~ Normal(mu=0.80, sd=0.03)
  - Comparator arm:   cost ~ Normal(mu= 700, sd=50), qaly ~ Normal(mu=0.65, sd=0.03)

Expected mean diffs: dCost ≈ +500, dQALY ≈ +0.15 (north-east quadrant).
With 500 bootstrap reps + fixed seed, the point estimate should be very
close to the true generating mean diffs, and 2.5/97.5 percentile CIs
should bracket them.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from research_api.services.economics.cost_qaly_regression import (
    bivariate_bootstrap,
)


def _make_two_arm_frame(seed: int = 17, n_per_arm: int = 120) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    intv_cost = rng.normal(1200.0, 50.0, n_per_arm)
    intv_qaly = rng.normal(0.80, 0.03, n_per_arm)
    comp_cost = rng.normal(700.0, 50.0, n_per_arm)
    comp_qaly = rng.normal(0.65, 0.03, n_per_arm)
    frame = pd.DataFrame(
        {
            "cost": np.concatenate([intv_cost, comp_cost]),
            "qaly": np.concatenate([intv_qaly, comp_qaly]),
            "treatment": (["intv"] * n_per_arm) + (["ctrl"] * n_per_arm),
        }
    )
    return frame


def test_bootstrap_point_estimate_matches_generating_means_within_se():
    """Point estimate (unadjusted) should sit near the true diff."""
    df = _make_two_arm_frame()
    out = bivariate_bootstrap(
        df,
        cost_col="cost",
        qaly_col="qaly",
        treatment_col="treatment",
        intervention_label="intv",
        comparator_label="ctrl",
        n_boot=500,
        seed=11,
    )
    # True dCost = 500. With ~120 per arm and sd=50, SE of mean diff ≈
    # sqrt(50^2/120 + 50^2/120) ≈ 6.5; we allow 4 SEs of slack.
    assert out["mean_cost_diff"] == pytest.approx(500.0, abs=30.0)
    # True dQALY = 0.15; SE ≈ sqrt(0.03^2/120 + 0.03^2/120) ≈ 0.004; 4 SEs.
    assert out["mean_qaly_diff"] == pytest.approx(0.15, abs=0.02)

    # CIs must bracket the point estimate and be of plausible width.
    ci_C_lo, ci_C_hi = out["ci_cost"]
    ci_Q_lo, ci_Q_hi = out["ci_qaly"]
    assert ci_C_lo < out["mean_cost_diff"] < ci_C_hi
    assert ci_Q_lo < out["mean_qaly_diff"] < ci_Q_hi
    # Plane has expected number of (non-NaN) reps.
    assert len(out["plane_bootstrap"]) >= 480


def test_bootstrap_plane_lives_in_NE_quadrant_for_NE_truth():
    """Generating means in the NE quadrant → vast majority of reps in NE."""
    df = _make_two_arm_frame()
    out = bivariate_bootstrap(
        df,
        cost_col="cost",
        qaly_col="qaly",
        treatment_col="treatment",
        intervention_label="intv",
        comparator_label="ctrl",
        n_boot=300,
        seed=42,
    )
    plane = out["plane_bootstrap"]
    ne_share = sum(1 for p in plane if p["dCost"] > 0 and p["dQALY"] > 0) / len(plane)
    assert ne_share > 0.95


def test_bootstrap_errors_when_columns_missing():
    df = pd.DataFrame({"cost": [1.0, 2.0], "qaly": [0.5, 0.6]})
    with pytest.raises(ValueError, match="treatment_col"):
        bivariate_bootstrap(
            df,
            cost_col="cost",
            qaly_col="qaly",
            treatment_col="arm",
            intervention_label="intv",
            comparator_label="ctrl",
            n_boot=10,
        )
