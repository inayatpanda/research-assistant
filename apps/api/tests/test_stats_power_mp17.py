"""Phase 17 (MP17) — Extended power families tests."""
from __future__ import annotations

import math

import pytest

from research_api.services.stats.power import (
    power_logrank,
    power_mixed_effects,
    power_noninferiority,
)


# ── Log-rank ────────────────────────────────────────────────────────────────


def test_power_logrank_required_events_known_value():
    """Schoenfeld: HR=0.6, alpha=0.05 (two-sided), power=0.8 → ~88 events."""
    res = power_logrank(0.6, alpha=0.05, power=0.80, event_rate=0.5)
    # Theory: d = (1.96+0.84)^2 * 4 / ln(0.6)^2 ≈ 7.84 * 4 / 0.2611 ≈ 120
    # With allocation_ratio=1: (1+1)^2 = 4 → ~120
    assert 100 <= res["required_events"] <= 140
    assert res["required_n"] > 0
    assert res["sensitivity_curve_png"].startswith(b"\x89PNG")


def test_power_logrank_more_events_needed_as_hr_approaches_one():
    res_strong = power_logrank(0.5, alpha=0.05, power=0.80, event_rate=0.5)
    res_weak = power_logrank(0.9, alpha=0.05, power=0.80, event_rate=0.5)
    assert res_weak["required_events"] > res_strong["required_events"]


def test_power_logrank_rejects_hr_one():
    with pytest.raises(ValueError):
        power_logrank(1.0, alpha=0.05, power=0.80, event_rate=0.5)


def test_power_logrank_rejects_event_rate_out_of_range():
    with pytest.raises(ValueError):
        power_logrank(0.5, event_rate=0.0)


# ── Mixed-effects cluster RCT ───────────────────────────────────────────────


def test_power_mixed_effects_design_effect_applied():
    """Design effect = 1 + (m-1)*ICC."""
    res = power_mixed_effects(
        0.5, n_per_cluster=20, n_clusters=10, icc=0.05, alpha=0.05, power=0.80
    )
    # DE = 1 + 19*0.05 = 1.95
    assert math.isclose(res["design_effect"], 1.95, abs_tol=1e-9)
    assert res["required_clusters_per_arm"] >= 1


def test_power_mixed_effects_inflates_with_higher_icc():
    res_low_icc = power_mixed_effects(
        0.5, n_per_cluster=20, n_clusters=10, icc=0.01, alpha=0.05, power=0.80
    )
    res_high_icc = power_mixed_effects(
        0.5, n_per_cluster=20, n_clusters=10, icc=0.20, alpha=0.05, power=0.80
    )
    assert res_high_icc["required_n"] > res_low_icc["required_n"]


def test_power_mixed_effects_rejects_invalid_icc():
    with pytest.raises(ValueError):
        power_mixed_effects(0.5, n_per_cluster=10, n_clusters=10, icc=1.5)


# ── Non-inferiority ─────────────────────────────────────────────────────────


def test_power_noninferiority_known_formula():
    """Hand-check the formula for margin=2, sigma=5, alpha=0.025, power=0.80, k=1:
    n_per_arm ≈ (1.96 + 0.84)^2 * 25 * 2 / 4 ≈ 98."""
    res = power_noninferiority(2.0, sigma=5.0, alpha=0.025, power=0.80)
    assert 90 <= res["required_n_per_group"] <= 110


def test_power_noninferiority_more_n_for_smaller_margin():
    res_wide = power_noninferiority(5.0, sigma=5.0, alpha=0.025, power=0.80)
    res_tight = power_noninferiority(1.0, sigma=5.0, alpha=0.025, power=0.80)
    assert res_tight["required_n_per_group"] > res_wide["required_n_per_group"]


def test_power_noninferiority_rejects_negative_margin():
    with pytest.raises(ValueError):
        power_noninferiority(-1.0, sigma=5.0)


def test_power_noninferiority_rejects_zero_sigma():
    with pytest.raises(ValueError):
        power_noninferiority(2.0, sigma=0.0)
