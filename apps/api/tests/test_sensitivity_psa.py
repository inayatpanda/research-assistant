"""Phase 18 (MP18) — PSA / DSA / scenario tests."""
from __future__ import annotations

import numpy as np
import pytest

from research_api.services.economics.sensitivity import dsa, psa, scenario


def test_psa_two_normal_params_distribution_shape_makes_sense():
    """Sample 1000 draws with two normally-distributed inputs and verify the
    summary statistics line up with the analytic mean / SE.

    base mean_cost_diff = 1000 (constant), base mean_qaly_diff = 0.05.
    We let mean_qaly_diff be drawn from Normal(mean=0.05, sd=0.01) — so the
    ICER (~20,000 £/QALY at point) should hover near 20,000 across the
    1000 draws, but with substantial spread because the denominator is
    small and noisy.
    """
    out = psa(
        base_inputs={"mean_cost_diff": 1000.0, "mean_qaly_diff": 0.05},
        parameter_distributions={
            "mean_qaly_diff": {"dist": "normal", "mean": 0.05, "sd": 0.01},
            "mean_cost_diff": {"dist": "normal", "mean": 1000.0, "sd": 50.0},
        },
        n_psa=1000,
        seed=7,
        wtp=30_000.0,
    )
    assert out["type"] == "psa"
    assert len(out["results"]) == 1000
    summ = out["summary"]
    # NMB = wtp * dQ - dC. mean NMB ≈ 30000*0.05 - 1000 = 500.
    assert summ["nmb_mean"] == pytest.approx(500.0, abs=80.0)
    # Fraction cost-effective at WTP=30000 should be solidly above 0.5
    # because mean NMB is positive and SD is moderate.
    assert summ["fraction_cost_effective"] > 0.7
    assert summ["fraction_cost_effective"] < 1.0
    # ICER mean ~ 20000.
    assert summ["icer_mean"] is not None
    assert summ["icer_mean"] == pytest.approx(20_000.0, rel=0.5)


def test_psa_seed_is_deterministic():
    """Same seed → identical draws."""
    spec = {
        "base_inputs": {"mean_cost_diff": 0.0, "mean_qaly_diff": 0.0},
        "parameter_distributions": {
            "mean_qaly_diff": {"dist": "normal", "mean": 0.1, "sd": 0.02}
        },
        "n_psa": 50,
        "seed": 99,
        "wtp": 20_000.0,
    }
    a = psa(**spec)  # type: ignore[arg-type]
    b = psa(**spec)  # type: ignore[arg-type]
    a_q = [r["mean_qaly_diff"] for r in a["results"]]
    b_q = [r["mean_qaly_diff"] for r in b["results"]]
    assert a_q == b_q


def test_dsa_two_params_tornado_shape():
    """One-way DSA produces per-param ranges suitable for a tornado chart."""
    out = dsa(
        base_inputs={"mean_cost_diff": 500.0, "mean_qaly_diff": 0.04},
        parameter_ranges={
            "mean_cost_diff": {"low": 300.0, "high": 700.0},
            "mean_qaly_diff": {"low": 0.02, "high": 0.06},
        },
        wtp=25_000.0,
    )
    assert out["type"] == "dsa"
    rows = {r["param"]: r for r in out["results"]}
    assert set(rows) == {"mean_cost_diff", "mean_qaly_diff"}
    # NMB at base = 25000 * 0.04 - 500 = 500.
    assert out["summary"]["base_nmb"] == pytest.approx(500.0)
    # Cost-diff sweep: low=300 (NMB=700), high=700 (NMB=300).
    assert rows["mean_cost_diff"]["low_nmb"] == pytest.approx(700.0)
    assert rows["mean_cost_diff"]["high_nmb"] == pytest.approx(300.0)


def test_scenario_overrides_apply_one_at_a_time():
    out = scenario(
        base_inputs={"mean_cost_diff": 1000.0, "mean_qaly_diff": 0.05},
        scenarios=[
            {"name": "best_case", "overrides": {"mean_qaly_diff": 0.10}},
            {"name": "worst_case", "overrides": {"mean_qaly_diff": 0.01}},
        ],
        wtp=30_000.0,
    )
    rows = {r["name"]: r for r in out["results"]}
    # best: dC=1000, dQ=0.10 → ICER=10000, NMB=30000*0.10-1000=2000
    assert rows["best_case"]["icer"] == pytest.approx(10_000.0)
    assert rows["best_case"]["nmb"] == pytest.approx(2_000.0)
    # worst: dC=1000, dQ=0.01 → ICER=100000, NMB=30000*0.01-1000=-700
    assert rows["worst_case"]["icer"] == pytest.approx(100_000.0)
    assert rows["worst_case"]["nmb"] == pytest.approx(-700.0)
