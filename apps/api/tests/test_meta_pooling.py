"""Pooling unit tests — hand-computed and Cochrane Handbook worked examples."""
import math

import pytest

from research_api.services.meta.effect_sizes import Effect
from research_api.services.meta.pooling import pool, pool_fixed, pool_random_dl


def _make(yi: float, vi: float, metric: str = "md") -> Effect:
    return Effect(yi=yi, vi=vi, se=math.sqrt(vi), metric=metric)


def test_pool_fixed_two_studies_known_answer():
    # yi=[0.5, 0.3], vi=[0.04, 0.05] → w=[25, 20]
    # yi_bar = (25*0.5 + 20*0.3) / 45 = 18.5/45 ≈ 0.4111
    # vi_bar = 1/45 ≈ 0.0222 → se ≈ 0.1491
    eff = [_make(0.5, 0.04), _make(0.3, 0.05)]
    res = pool_fixed(eff)
    assert res.estimate == pytest.approx(0.41111, abs=1e-4)
    assert res.se == pytest.approx(0.14907, abs=1e-4)
    assert res.model == "fixed"
    assert math.isclose(sum(res.weights), 1.0, abs_tol=1e-9)


def test_pool_random_dl_known_answer():
    # Two-study DL: identical inputs → tau^2 should be 0 → matches fixed
    eff = [_make(0.5, 0.04), _make(0.5, 0.04)]
    fixed = pool_fixed(eff)
    random = pool_random_dl(eff)
    assert random.estimate == pytest.approx(fixed.estimate, abs=1e-6)
    assert random.se == pytest.approx(fixed.se, abs=1e-6)


def test_pool_random_collapses_to_fixed_when_tau2_zero():
    # Heterogeneous magnitude difference is small; tau^2 should be ~0
    eff = [_make(0.5, 0.04), _make(0.5, 0.04), _make(0.5, 0.04)]
    f = pool_fixed(eff)
    r = pool_random_dl(eff)
    assert r.estimate == pytest.approx(f.estimate, abs=1e-6)


def test_pool_weights_sum_to_one():
    eff = [_make(0.1, 0.02), _make(0.3, 0.03), _make(0.2, 0.04)]
    res = pool_fixed(eff)
    assert math.isclose(sum(res.weights), 1.0, abs_tol=1e-9)


def test_pool_p_value_two_sided():
    # A z near 1.96 should yield p near 0.05; symmetric for negative z
    pos = pool_fixed([_make(0.4, 0.04), _make(0.4, 0.04)])
    neg = pool_fixed([_make(-0.4, 0.04), _make(-0.4, 0.04)])
    assert pos.p == pytest.approx(neg.p, abs=1e-6)
    assert 0 <= pos.p <= 1


def test_pool_raises_on_single_study():
    with pytest.raises(ValueError):
        pool_fixed([_make(0.5, 0.04)])


def test_pool_raises_on_zero_variance():
    with pytest.raises(ValueError):
        pool_fixed([_make(0.5, 0.0), _make(0.4, 0.05)])


def test_pool_dispatch():
    eff = [_make(0.5, 0.04), _make(0.3, 0.05)]
    assert pool(eff, "fixed").model == "fixed"
    assert pool(eff, "random").model == "random"
    with pytest.raises(ValueError):
        pool(eff, "bogus")
