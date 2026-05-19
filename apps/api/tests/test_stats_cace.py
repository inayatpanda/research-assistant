"""Phase 17 (MP17) — CACE / 2SLS tests."""
from __future__ import annotations

import math

import numpy as np
import pytest

from research_api.services.stats.cace import run_cace_2sls


def _generate_cace_data(
    *,
    n: int = 400,
    cace_truth: float = 2.0,
    compliance_rate: float = 0.6,
    seed: int = 0,
):
    rng = np.random.default_rng(seed)
    z = rng.integers(0, 2, n).astype(float)
    # Compliance: in arm Z=1, fraction `compliance_rate` actually take treatment.
    treated_if_assigned = (rng.random(n) < compliance_rate).astype(float)
    # In arm Z=0, ~10% always-takers receive treatment anyway.
    treated_if_control = (rng.random(n) < 0.1).astype(float)
    d = np.where(z == 1, treated_if_assigned, treated_if_control)
    # Outcome with true CACE.
    y = 1.0 + cace_truth * d + rng.normal(0, 1.0, n)
    return y, d, z


def test_run_cace_2sls_recovers_known_effect():
    y, d, z = _generate_cace_data(n=2000, cace_truth=2.0, compliance_rate=0.7, seed=1)
    res = run_cace_2sls(y=y, d=d, z=z)
    assert math.isclose(res["cace_estimate"], 2.0, abs_tol=0.3)
    assert res["se"] > 0
    assert res["p"] < 0.001
    assert res["compliance_rate"] > 0.4


def test_run_cace_2sls_n_reflects_complete_cases():
    y, d, z = _generate_cace_data(n=300, seed=2)
    y[0] = float("nan")
    res = run_cace_2sls(y=y, d=d, z=z)
    assert res["n"] == 299


def test_run_cace_2sls_rejects_no_compliance():
    """Compliance_rate = 0 → estimator is unidentified."""
    rng = np.random.default_rng(0)
    n = 200
    z = rng.integers(0, 2, n).astype(float)
    d = np.zeros(n)  # nobody complies in either arm
    y = rng.normal(0, 1, n)
    with pytest.raises(ValueError, match="compliance"):
        run_cace_2sls(y=y, d=d, z=z)


def test_run_cace_2sls_validates_shapes():
    with pytest.raises(ValueError, match="shape"):
        run_cace_2sls(
            y=np.zeros(10), d=np.zeros(10), z=np.zeros(11)
        )


def test_run_cace_2sls_rejects_tiny_n():
    with pytest.raises(ValueError, match="at least"):
        run_cace_2sls(
            y=np.zeros(5), d=np.zeros(5), z=np.array([0, 1, 0, 1, 0], dtype=float)
        )


def test_run_cace_2sls_returns_itt_rates():
    y, d, z = _generate_cace_data(n=600, compliance_rate=0.8, seed=4)
    res = run_cace_2sls(y=y, d=d, z=z)
    # ITT D|Z=1 should be ~0.8; D|Z=0 should be ~0.1.
    assert math.isclose(res["itt_d_z1"], 0.8, abs_tol=0.1)
    assert math.isclose(res["itt_d_z0"], 0.1, abs_tol=0.1)
