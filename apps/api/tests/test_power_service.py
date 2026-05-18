"""Phase 13 — Power calculator known-answer tests.

Cohen's textbook benchmarks for the five test families. Each `required_n`
value comes straight from statsmodels.stats.power and is reproduced here
so a regression in the wrapper math is caught immediately.
"""
from __future__ import annotations

import base64
import math

import pytest

from research_api.services.stats.power import (
    power_anova,
    power_chi_square,
    power_correlation,
    power_ttest_ind,
    power_ttest_paired,
)


def _png_is_valid(raw: bytes) -> bool:
    return raw.startswith(b"\x89PNG\r\n\x1a\n") and len(raw) > 1000


# ── ttest_ind: Cohen's d ──────────────────────────────────────────────────


@pytest.mark.parametrize(
    "effect_size,expected_n_per_group",
    [
        (0.2, 394),   # small effect
        (0.5, 64),    # medium effect
        (0.8, 26),    # large effect
    ],
)
def test_power_ttest_ind_known_answers(effect_size: float, expected_n_per_group: int):
    r = power_ttest_ind(effect_size)
    assert r["required_n_per_group"] == expected_n_per_group
    assert r["required_n"] == expected_n_per_group * 2
    assert _png_is_valid(r["sensitivity_curve_png"])
    assert math.isclose(r["alpha"], 0.05)
    assert math.isclose(r["power"], 0.80)


def test_power_ttest_ind_rejects_zero_effect():
    with pytest.raises(ValueError):
        power_ttest_ind(0.0)


def test_power_ttest_ind_rejects_negative_alpha():
    with pytest.raises(ValueError):
        power_ttest_ind(0.5, alpha=-0.1)


# ── ttest_paired ──────────────────────────────────────────────────────────


def test_power_ttest_paired_medium_effect():
    r = power_ttest_paired(0.5)
    # statsmodels TTestPower at dz=0.5 alpha=0.05 power=0.80 -> 34 (two-sided)
    assert r["required_n"] == 34
    assert r["required_n_per_group"] is None
    assert _png_is_valid(r["sensitivity_curve_png"])


# ── ANOVA: Cohen's f ──────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "effect_size,k_groups,expected_n_per_group",
    [
        (0.25, 3, 53),
        (0.40, 4, 19),
    ],
)
def test_power_anova_known_answers(effect_size: float, k_groups: int, expected_n_per_group: int):
    r = power_anova(effect_size, k_groups=k_groups)
    assert r["required_n_per_group"] == expected_n_per_group
    assert r["required_n"] == expected_n_per_group * k_groups
    assert _png_is_valid(r["sensitivity_curve_png"])


def test_power_anova_rejects_one_group():
    with pytest.raises(ValueError):
        power_anova(0.25, k_groups=1)


# ── chi-square goodness-of-fit (Cohen's w) ────────────────────────────────


def test_power_chi_square_medium_w():
    # Cohen's w=0.3 at df=3 (4 bins), alpha=0.05, power=0.80 -> 122
    r = power_chi_square(0.3, df=3)
    assert r["required_n"] == 122
    assert _png_is_valid(r["sensitivity_curve_png"])


def test_power_chi_square_rejects_invalid_df():
    with pytest.raises(ValueError):
        power_chi_square(0.3, df=0)


# ── correlation via Fisher z ─────────────────────────────────────────────


def test_power_correlation_r_0_3():
    # Standard reference (Cohen 1988): r=0.3, alpha=0.05, power=0.80 -> n=85
    r = power_correlation(0.3)
    assert r["required_n"] == 85
    assert _png_is_valid(r["sensitivity_curve_png"])


def test_power_correlation_rejects_r_geq_1():
    with pytest.raises(ValueError):
        power_correlation(1.0)


# ── HTTP route (round-trip + PNG data URI) ────────────────────────────────


@pytest.mark.asyncio
async def test_power_route_ttest_ind(client):
    r = await client.post(
        "/api/power",
        json={"test_family": "ttest_ind", "effect_size": 0.5},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["required_n_per_group"] == 64
    assert data["required_n"] == 128
    assert data["sensitivity_curve_png"].startswith("data:image/png;base64,")
    raw = base64.b64decode(data["sensitivity_curve_png"].split(",", 1)[1])
    assert raw.startswith(b"\x89PNG\r\n\x1a\n")


@pytest.mark.asyncio
async def test_power_route_anova_requires_k_groups(client):
    r = await client.post(
        "/api/power",
        json={"test_family": "anova", "effect_size": 0.25},
    )
    assert r.status_code == 400
    assert "k_groups" in r.json()["detail"]


@pytest.mark.asyncio
async def test_power_route_chi_square_requires_df(client):
    r = await client.post(
        "/api/power",
        json={"test_family": "chi_square", "effect_size": 0.3},
    )
    assert r.status_code == 400
    assert "df" in r.json()["detail"]
