"""Phase 18 (MP18) — ICER + NMB + dominance quadrant tests."""
from __future__ import annotations

import math

import pytest

from research_api.services.economics.icer import (
    compute_icer,
    compute_nmb,
    nmb_at_thresholds,
)


def test_icer_dominant_quadrant_nw():
    """Cheaper AND more effective → dominant; no ICER reported."""
    res = compute_icer(mean_cost_diff=-500.0, mean_qaly_diff=0.05)
    assert res["dominance_status"] == "dominant"
    assert res["icer"] is None


def test_icer_dominated_quadrant_se():
    """More expensive AND less effective → dominated."""
    res = compute_icer(mean_cost_diff=800.0, mean_qaly_diff=-0.02)
    assert res["dominance_status"] == "dominated"
    assert res["icer"] is None


def test_icer_northeast_positive_ratio():
    """NE: more expensive but more effective → +ICER, compare to WTP."""
    res = compute_icer(mean_cost_diff=4500.0, mean_qaly_diff=0.15)
    assert res["dominance_status"] == "northeast"
    assert res["icer"] == pytest.approx(30000.0, abs=1e-9)


def test_icer_southwest_negative_ratio():
    """SW: cheaper but less effective → ICER positive arithmetically."""
    res = compute_icer(mean_cost_diff=-300.0, mean_qaly_diff=-0.03)
    assert res["dominance_status"] == "southwest"
    # -300 / -0.03 = +10000
    assert res["icer"] == pytest.approx(10000.0, abs=1e-9)


def test_icer_zero_qaly_diff_returns_inf():
    """When dQALY=0 but dC ≠ 0 we report +/- infinity with a quadrant tag."""
    res_pos = compute_icer(mean_cost_diff=1000.0, mean_qaly_diff=0.0)
    assert math.isinf(res_pos["icer"])
    assert res_pos["dominance_status"] == "northeast"
    res_neg = compute_icer(mean_cost_diff=-1000.0, mean_qaly_diff=0.0)
    assert math.isinf(res_neg["icer"])
    assert res_neg["dominance_status"] == "southwest"


def test_nmb_basic_formula():
    """NMB = wtp*dQ - dC."""
    nmb = compute_nmb(mean_cost_diff=4500.0, mean_qaly_diff=0.15, wtp_threshold=30000)
    # 30000 * 0.15 - 4500 = 4500 - 4500 = 0
    assert nmb == pytest.approx(0.0, abs=1e-9)
    nmb_high = compute_nmb(
        mean_cost_diff=4500.0, mean_qaly_diff=0.15, wtp_threshold=50000
    )
    # 50000 * 0.15 - 4500 = 7500 - 4500 = 3000
    assert nmb_high == pytest.approx(3000.0, abs=1e-9)


def test_nmb_at_thresholds_keyed_by_threshold():
    out = nmb_at_thresholds(
        mean_cost_diff=2000.0,
        mean_qaly_diff=0.1,
        thresholds=[20000, 30000, 50000],
    )
    # 20000*0.1 - 2000 = 0
    # 30000*0.1 - 2000 = 1000
    # 50000*0.1 - 2000 = 3000
    assert out == {"20000": pytest.approx(0.0), "30000": pytest.approx(1000.0), "50000": pytest.approx(3000.0)}
