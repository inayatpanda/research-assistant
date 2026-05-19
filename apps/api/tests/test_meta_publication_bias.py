"""Phase 19 (MP19) — Publication-bias tests (Egger / Harbord / Begg / Peters)."""
from __future__ import annotations

import math

import pytest

from research_api.services.meta.publication_bias import (
    begg_test,
    egger_test,
    harbord_test,
    peters_test,
    select_test_for_metric,
)


# ── Egger ──────────────────────────────────────────────────────────────


def test_egger_symmetric_funnel_close_to_zero():
    # Symmetric: large-SE studies straddle zero just like small-SE ones.
    effects = [0.0, 0.05, -0.05, 0.02, -0.02]
    ses = [0.05, 0.1, 0.1, 0.2, 0.2]
    res = egger_test(effects, ses)
    assert res.method == "egger"
    assert abs(res.statistic) < 1.0
    assert res.p > 0.1


def test_egger_asymmetric_funnel_returns_nonzero_intercept():
    # Asymmetric — small studies (large SE) carry larger positive effects.
    effects = [0.10, 0.20, 0.45, 0.80, 1.20]
    ses = [0.05, 0.08, 0.15, 0.25, 0.40]
    res = egger_test(effects, ses)
    assert res.method == "egger"
    # With monotone increase, the intercept must be non-trivial
    assert abs(res.statistic) > 0.1


def test_egger_needs_three_studies():
    with pytest.raises(ValueError):
        egger_test([0.1, 0.2], [0.1, 0.1])


def test_egger_rejects_nonpositive_se():
    with pytest.raises(ValueError):
        egger_test([0.1, 0.2, 0.3], [0.1, 0.0, 0.1])


# ── Begg ───────────────────────────────────────────────────────────────


def test_begg_symmetric_funnel():
    effects = [0.0, 0.05, -0.05, 0.02, -0.02, 0.01, -0.01]
    ses = [0.05, 0.1, 0.1, 0.2, 0.2, 0.3, 0.3]
    res = begg_test(effects, ses)
    assert res.method == "begg"
    assert -1.0 < res.statistic < 1.0
    assert 0.0 <= res.p <= 1.0


def test_begg_needs_four_studies():
    with pytest.raises(ValueError):
        begg_test([0.1, 0.2, 0.3], [0.1, 0.1, 0.1])


# ── Harbord ────────────────────────────────────────────────────────────


def test_harbord_symmetric_or_close_to_zero():
    # Six balanced 2x2 tables with roughly equal events
    events_t = [10, 15, 20, 25, 30, 35]
    n_t = [100, 100, 100, 100, 100, 100]
    events_c = [12, 14, 18, 24, 32, 36]
    n_c = [100, 100, 100, 100, 100, 100]
    res = harbord_test(events_t, n_t, events_c, n_c)
    assert res.method == "harbord"
    assert abs(res.statistic) < 2.0


def test_harbord_validates_lengths():
    with pytest.raises(ValueError):
        harbord_test([1, 2], [10, 20, 30], [1, 1, 1], [10, 10, 10])


def test_harbord_needs_three_studies():
    with pytest.raises(ValueError):
        harbord_test([5, 10], [100, 100], [5, 10], [100, 100])


# ── Peters ─────────────────────────────────────────────────────────────


def test_peters_returns_intercept_and_p():
    events = [25, 40, 50, 60, 75]
    totals = [200, 200, 200, 200, 200]
    log_or = [0.10, 0.15, 0.30, 0.20, 0.25]
    res = peters_test(events, totals, log_or=log_or)
    assert res.method == "peters"
    assert math.isfinite(res.statistic)
    assert 0.0 <= res.p <= 1.0


def test_peters_validates_log_or_provided():
    with pytest.raises(ValueError):
        peters_test([10, 20, 30], [100, 100, 100], log_or=None)


def test_peters_validates_lengths():
    with pytest.raises(ValueError):
        peters_test([10, 20, 30], [100, 100, 100], log_or=[0.1, 0.2])


def test_peters_rejects_invalid_events():
    with pytest.raises(ValueError):
        peters_test([110, 20, 30], [100, 100, 100], log_or=[0.1, 0.2, 0.3])


# ── select_test_for_metric ─────────────────────────────────────────────


def test_select_for_continuous_picks_egger():
    assert select_test_for_metric("md") == "egger"
    assert select_test_for_metric("smd") == "egger"
    assert select_test_for_metric("r") == "egger"


def test_select_for_binary_picks_harbord():
    assert select_test_for_metric("or") == "harbord"
    assert select_test_for_metric("rr") == "harbord"


def test_select_for_hr_picks_egger():
    assert select_test_for_metric("hr") == "egger"
