"""Phase 18 (MP18) — Bivariate cost-QALY bootstrap.

Estimates the *mean* cost difference and *mean* QALY difference between
the intervention and comparator arms, with bootstrap CIs. Optionally
adjusts for baseline covariates by running per-outcome OLS (statsmodels
isn't required — we use NumPy/SciPy directly to avoid pulling extra
deps, mirroring `services/stats/runner.py`'s approach).

The result is the standard *cost-effectiveness plane* — a cloud of
(dCost, dQALY) points that downstream services use to build the CEAC
and render the plane chart.

References:
- Glick HA, Doshi JA, Sonnad SS, Polsky D. *Economic Evaluation in
  Clinical Trials*. Oxford University Press, 2014 — chapter on
  non-parametric bootstrap.
- Manca A, Hawkins N, Sculpher MJ. Estimating mean QALYs in trial-based
  cost-effectiveness analysis. Health Economics, 2005.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def _arm_means(
    df: pd.DataFrame,
    *,
    cost_col: str,
    qaly_col: str,
    treatment_col: str,
    intervention_label: str,
    comparator_label: str,
) -> tuple[float, float]:
    """Return (mean_cost_diff, mean_qaly_diff) for one resample.

    Unadjusted: simple arm means. The intervention - comparator convention
    is preserved so a positive QALY-diff means the intervention is
    *better*, and a negative cost-diff means the intervention is
    *cheaper* (south-west quadrant cost-saving).
    """
    grp = df.groupby(treatment_col, dropna=False)
    if intervention_label not in grp.groups or comparator_label not in grp.groups:
        return float("nan"), float("nan")
    i = grp.get_group(intervention_label)
    c = grp.get_group(comparator_label)
    dC = float(i[cost_col].mean()) - float(c[cost_col].mean())
    dQ = float(i[qaly_col].mean()) - float(c[qaly_col].mean())
    return dC, dQ


def _adjusted_arm_means(
    df: pd.DataFrame,
    *,
    cost_col: str,
    qaly_col: str,
    treatment_col: str,
    intervention_label: str,
    comparator_label: str,
    baseline_covariates: list[str],
) -> tuple[float, float]:
    """OLS-adjusted treatment effect on cost and QALY.

    We fit two separate OLS regressions (one per outcome) with an
    intercept, a treatment dummy, and the supplied baseline covariates.
    The treatment dummy coefficient = mean diff after covariate
    adjustment. No statsmodels needed: solve via NumPy's lstsq.
    """
    sub = df.dropna(subset=[cost_col, qaly_col, treatment_col, *baseline_covariates])
    if len(sub) < 2 + len(baseline_covariates):
        return _arm_means(
            sub,
            cost_col=cost_col,
            qaly_col=qaly_col,
            treatment_col=treatment_col,
            intervention_label=intervention_label,
            comparator_label=comparator_label,
        )
    # Treatment indicator: 1 for intervention, 0 for comparator.
    t = (sub[treatment_col] == intervention_label).astype(float).to_numpy()
    cov_mat: list[np.ndarray] = []
    for c in baseline_covariates:
        col = sub[c].to_numpy(dtype=float)
        cov_mat.append(col)
    intercept = np.ones(len(sub), dtype=float)
    X = np.column_stack([intercept, t, *cov_mat]) if cov_mat else np.column_stack([intercept, t])

    def _coef(y: np.ndarray) -> float:
        # treatment coefficient is index 1
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        return float(beta[1])

    dC = _coef(sub[cost_col].to_numpy(dtype=float))
    dQ = _coef(sub[qaly_col].to_numpy(dtype=float))
    return dC, dQ


def bivariate_bootstrap(
    df: pd.DataFrame,
    *,
    cost_col: str,
    qaly_col: str,
    treatment_col: str,
    intervention_label: str,
    comparator_label: str,
    n_boot: int = 1000,
    seed: int = 42,
    baseline_covariates: list[str] | None = None,
) -> dict[str, Any]:
    """Bootstrap the (cost, QALY) treatment effect.

    Returns:
        {
          mean_cost_diff: float,         # point estimate from full sample
          mean_qaly_diff: float,
          plane_bootstrap: list[{dCost, dQALY}],  # n_boot reps
          ci_cost: (low, high),          # 2.5 / 97.5 percentile
          ci_qaly: (low, high),
        }
    """
    if cost_col not in df.columns:
        raise ValueError(f"cost_col {cost_col!r} not in frame")
    if qaly_col not in df.columns:
        raise ValueError(f"qaly_col {qaly_col!r} not in frame")
    if treatment_col not in df.columns:
        raise ValueError(f"treatment_col {treatment_col!r} not in frame")
    if n_boot < 1:
        raise ValueError("n_boot must be >= 1")

    work = df.dropna(subset=[cost_col, qaly_col, treatment_col]).reset_index(drop=True)
    if work.empty:
        raise ValueError("no rows with non-null cost / qaly / treatment")

    covariates = baseline_covariates or []
    rng = np.random.default_rng(seed)

    def _one_estimate(sample: pd.DataFrame) -> tuple[float, float]:
        if covariates:
            return _adjusted_arm_means(
                sample,
                cost_col=cost_col,
                qaly_col=qaly_col,
                treatment_col=treatment_col,
                intervention_label=intervention_label,
                comparator_label=comparator_label,
                baseline_covariates=covariates,
            )
        return _arm_means(
            sample,
            cost_col=cost_col,
            qaly_col=qaly_col,
            treatment_col=treatment_col,
            intervention_label=intervention_label,
            comparator_label=comparator_label,
        )

    # Point estimate from full data.
    point_dC, point_dQ = _one_estimate(work)

    reps_C: list[float] = []
    reps_Q: list[float] = []
    plane: list[dict[str, float]] = []
    n = len(work)
    for _ in range(int(n_boot)):
        idx = rng.integers(0, n, size=n)
        sample = work.iloc[idx].reset_index(drop=True)
        dC, dQ = _one_estimate(sample)
        if np.isnan(dC) or np.isnan(dQ):
            continue
        reps_C.append(dC)
        reps_Q.append(dQ)
        plane.append({"dCost": dC, "dQALY": dQ})

    if not reps_C:
        raise ValueError(
            "all bootstrap replicates produced NaN — check treatment labels match data"
        )
    arr_C = np.asarray(reps_C)
    arr_Q = np.asarray(reps_Q)
    ci_C = (float(np.percentile(arr_C, 2.5)), float(np.percentile(arr_C, 97.5)))
    ci_Q = (float(np.percentile(arr_Q, 2.5)), float(np.percentile(arr_Q, 97.5)))
    return {
        "mean_cost_diff": float(point_dC),
        "mean_qaly_diff": float(point_dQ),
        "plane_bootstrap": plane,
        "ci_cost": ci_C,
        "ci_qaly": ci_Q,
    }


__all__ = ["bivariate_bootstrap"]
