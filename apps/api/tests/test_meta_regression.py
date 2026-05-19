"""Phase 19 (MP19) — Meta-regression weighted-OLS test."""
from __future__ import annotations

import math

import pytest

from research_api.services.meta import effect_sizes as es
from research_api.services.meta.meta_regression import meta_regression


def _eff(yi: float, se: float) -> es.Effect:
    return es.Effect(yi=yi, se=se, vi=se * se, metric="md")


def test_meta_regression_recovers_positive_slope():
    # yi = 0.5 * x with low noise — slope should land near 0.5
    moderator = [1.0, 2.0, 3.0, 4.0, 5.0]
    effects = [_eff(0.5 * x, 0.05) for x in moderator]
    res = meta_regression(effects, moderator, model="fixed")
    assert res.coef == pytest.approx(0.5, abs=0.05)
    assert res.p < 0.01
    assert res.r2 > 0.95
    assert res.n == 5
    assert res.bubble_plot_png.startswith(b"\x89PNG")


def test_meta_regression_flat_moderator_no_significant_slope():
    moderator = [1.0, 2.0, 3.0, 4.0, 5.0]
    effects = [_eff(0.2, 0.1) for _ in moderator]
    res = meta_regression(effects, moderator, model="fixed")
    assert math.isfinite(res.coef)
    assert res.p > 0.05


def test_meta_regression_requires_three_studies():
    moderator = [1.0, 2.0]
    effects = [_eff(0.1, 0.1), _eff(0.2, 0.1)]
    with pytest.raises(ValueError):
        meta_regression(effects, moderator, model="fixed")


def test_meta_regression_rejects_length_mismatch():
    moderator = [1.0, 2.0]
    effects = [_eff(0.1, 0.1), _eff(0.2, 0.1), _eff(0.3, 0.1)]
    with pytest.raises(ValueError):
        meta_regression(effects, moderator, model="fixed")


def test_random_model_accepts():
    moderator = [1.0, 2.0, 3.0, 4.0]
    effects = [_eff(0.1 + x * 0.2, 0.1) for x in moderator]
    res = meta_regression(effects, moderator, model="random")
    assert math.isfinite(res.coef)
    assert math.isfinite(res.se)


def test_unknown_model_raises():
    moderator = [1.0, 2.0, 3.0]
    effects = [_eff(0.1, 0.1)] * 3
    with pytest.raises(ValueError):
        meta_regression(effects, moderator, model="bayes")
