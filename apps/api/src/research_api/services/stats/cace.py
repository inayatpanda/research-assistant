"""Phase 17 (MP17) — Compliance-adjusted causal effect via 2SLS.

The Complier-Average Causal Effect (CACE) is estimated by instrumenting
``treatment_received`` with the randomised ``treatment_assigned`` using
statsmodels' classic ``IV2SLS`` from ``sandbox.regression.gmm``.

Inputs are 1-D NumPy arrays:
  - Y: outcome (continuous)
  - D: indicator of treatment-received (0/1)
  - Z: indicator of randomised-assignment (0/1)

Outputs: ``{cace_estimate, se, p, compliance_rate, n}``.
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np


def run_cace_2sls(
    *,
    y: np.ndarray,
    d: np.ndarray,
    z: np.ndarray,
) -> dict[str, Any]:
    """Estimate CACE = beta on the instrumented D column.

    ``compliance_rate`` is computed as the mean of ``D|Z=1`` — ``D|Z=0`` (the
    Wald/IV estimand's denominator); it must be > 0 for the estimator to be
    identified.
    """
    from statsmodels.sandbox.regression.gmm import IV2SLS

    y = np.asarray(y, dtype=float)
    d = np.asarray(d, dtype=float)
    z = np.asarray(z, dtype=float)
    if not (y.shape == d.shape == z.shape):
        raise ValueError("y, d, z must all have the same shape")
    n = int(y.shape[0])
    if n < 10:
        raise ValueError("CACE requires at least 10 observations")
    mask = ~(np.isnan(y) | np.isnan(d) | np.isnan(z))
    y, d, z = y[mask], d[mask], z[mask]
    n_used = int(y.shape[0])

    treated_rate_z1 = float(np.mean(d[z == 1])) if np.any(z == 1) else float("nan")
    treated_rate_z0 = float(np.mean(d[z == 0])) if np.any(z == 0) else float("nan")
    compliance = treated_rate_z1 - treated_rate_z0
    if not math.isfinite(compliance) or compliance <= 0:
        raise ValueError(
            "compliance rate (P[D=1|Z=1] - P[D=1|Z=0]) must be > 0 to identify CACE"
        )

    exog = np.column_stack([np.ones(n_used), d])
    instr = np.column_stack([np.ones(n_used), z])
    fit = IV2SLS(y, exog, instr).fit()
    # First non-intercept slope is the IV estimator of D's coefficient.
    cace = float(fit.params[1])
    se = float(fit.bse[1])
    p = float(fit.pvalues[1])
    return {
        "cace_estimate": cace,
        "se": se,
        "p": p,
        "compliance_rate": float(compliance),
        "n": n_used,
        "itt_d_z1": treated_rate_z1,
        "itt_d_z0": treated_rate_z0,
    }


__all__ = ["run_cace_2sls"]
