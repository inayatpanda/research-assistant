"""Heterogeneity unit tests."""
import math

import pytest

from research_api.services.meta.effect_sizes import Effect
from research_api.services.meta.heterogeneity import heterogeneity


def _make(yi: float, vi: float, metric: str = "md") -> Effect:
    return Effect(yi=yi, vi=vi, se=math.sqrt(vi), metric=metric)


def test_q_zero_when_studies_identical():
    eff = [_make(0.5, 0.04), _make(0.5, 0.04), _make(0.5, 0.04)]
    het = heterogeneity(eff)
    assert het.q == pytest.approx(0.0, abs=1e-9)
    assert het.i2 == pytest.approx(0.0, abs=1e-9)
    assert het.tau2 == pytest.approx(0.0, abs=1e-9)
    assert het.df == 2


def test_q_matches_handbook_worked_example():
    # Two studies with weights 25 and 20, yi 0.5 and 0.3 → yi_fixed = 0.4111
    # Q = 25*(0.5-0.4111)^2 + 20*(0.3-0.4111)^2 = 25*0.00790 + 20*0.01235 = 0.1976 + 0.2469 = 0.4444
    eff = [_make(0.5, 0.04), _make(0.3, 0.05)]
    het = heterogeneity(eff)
    assert het.q == pytest.approx(0.4444, abs=1e-3)


def test_i2_clipped_at_zero():
    # df=2, Q=0.4 → (Q - df)/Q < 0 → clipped to 0
    eff = [_make(0.4, 0.04), _make(0.5, 0.05), _make(0.45, 0.06)]
    het = heterogeneity(eff)
    assert het.i2 >= 0.0
    if het.q < het.df:
        assert het.i2 == 0.0


def test_i2_at_100_for_extreme_disagreement():
    # Very heterogeneous: yi values miles apart with tiny variances
    eff = [_make(-5.0, 0.0001), _make(5.0, 0.0001)]
    het = heterogeneity(eff)
    assert het.i2 > 99.0


def test_tau2_zero_when_homogeneous():
    eff = [_make(0.5, 0.04), _make(0.5, 0.04)]
    het = heterogeneity(eff)
    assert het.tau2 == pytest.approx(0.0, abs=1e-9)


def test_tau2_nonzero_when_heterogeneous():
    eff = [_make(-2.0, 0.01), _make(2.0, 0.01)]
    het = heterogeneity(eff)
    assert het.tau2 > 0.0


def test_p_value_decreases_as_q_grows():
    eff_homogeneous = [_make(0.5, 0.04), _make(0.51, 0.04)]
    eff_heterogeneous = [_make(-1.0, 0.04), _make(1.0, 0.04)]
    p_homo = heterogeneity(eff_homogeneous).p
    p_hetero = heterogeneity(eff_heterogeneous).p
    assert p_hetero < p_homo


def test_heterogeneity_requires_two_studies():
    with pytest.raises(ValueError):
        heterogeneity([_make(0.5, 0.04)])
