"""Effect-size unit tests.

References: Cochrane Handbook for Systematic Reviews of Interventions v6.3, Ch.10.
"""
import math

import pytest

from research_api.services.meta import effect_sizes as es


def test_md_known_answer():
    # Cochrane-style worked example: yi = 5 - 3 = 2; vi = 4/20 + 4/20 = 0.4
    eff = es.md(mean_a=5.0, sd_a=2.0, n_a=20, mean_b=3.0, sd_b=2.0, n_b=20)
    assert eff.metric == "md"
    assert eff.yi == pytest.approx(2.0, rel=1e-6)
    assert eff.vi == pytest.approx(0.4, rel=1e-6)
    assert eff.se == pytest.approx(math.sqrt(0.4), rel=1e-6)


def test_md_raises_on_zero_n():
    with pytest.raises(ValueError):
        es.md(mean_a=1.0, sd_a=1.0, n_a=0, mean_b=0.0, sd_b=1.0, n_b=10)


def test_smd_hedges_g_matches_handbook():
    # Cochrane §10.5 worked example values
    eff = es.smd_hedges_g(mean_a=10.0, sd_a=4.0, n_a=40, mean_b=8.0, sd_b=4.0, n_b=40)
    # s_p = 4, d = 0.5, J = 1 - 3/(4*78 - 1) = 1 - 3/311 ≈ 0.99035
    # g ≈ 0.49518; vi = 80/(40*40) + g^2 / (2*80) = 0.05 + 0.001532 ≈ 0.05153
    assert eff.yi == pytest.approx(0.49518, abs=1e-3)
    assert eff.vi == pytest.approx(0.05153, abs=1e-3)


def test_smd_small_sample_correction_applied():
    # With small n the Hedges correction should make |g| < |d|
    d_no_correction_eff = es.smd_hedges_g(
        mean_a=2.0, sd_a=1.0, n_a=5, mean_b=1.0, sd_b=1.0, n_b=5,
    )
    raw_d = 1.0
    assert abs(d_no_correction_eff.yi) < abs(raw_d)


def test_smd_raises_on_negative_sd():
    with pytest.raises(ValueError):
        es.smd_hedges_g(mean_a=1.0, sd_a=-1.0, n_a=10, mean_b=0.0, sd_b=1.0, n_b=10)


def test_odds_ratio_known_answer():
    # 2x2 table: a=20, n_a=100, b=10, n_b=100 → OR = (20/80) / (10/90) = 2.25
    eff = es.odds_ratio(events_a=20, n_a=100, events_b=10, n_b=100)
    assert eff.metric == "or"
    assert eff.yi == pytest.approx(math.log(2.25), abs=1e-6)
    expected_vi = 1 / 20 + 1 / 80 + 1 / 10 + 1 / 90
    assert eff.vi == pytest.approx(expected_vi, abs=1e-6)


def test_odds_ratio_zero_cell_continuity_correction():
    # events_a = 0 → continuity correction kicks in. Result should be finite.
    eff = es.odds_ratio(events_a=0, n_a=50, events_b=5, n_b=50)
    assert math.isfinite(eff.yi)
    assert math.isfinite(eff.vi)
    assert eff.vi > 0


def test_risk_ratio_known_answer():
    # a=20/100=0.2, b=10/100=0.1 → RR = 2.0; log_rr = log(2)
    eff = es.risk_ratio(events_a=20, n_a=100, events_b=10, n_b=100)
    assert eff.metric == "rr"
    assert eff.yi == pytest.approx(math.log(2.0), abs=1e-6)
    expected_vi = 1 / 20 - 1 / 100 + 1 / 10 - 1 / 100
    assert eff.vi == pytest.approx(expected_vi, abs=1e-6)


def test_hazard_ratio_from_logs_passthrough():
    eff = es.hazard_ratio_from_logs(log_hr=-0.3567, se_log_hr=0.1233)
    assert eff.metric == "hr"
    assert eff.yi == pytest.approx(-0.3567, abs=1e-6)
    assert eff.se == pytest.approx(0.1233, abs=1e-6)
    assert eff.vi == pytest.approx(0.1233 ** 2, abs=1e-8)


def test_hazard_ratio_from_ci_back_calculates_se():
    # HR=0.70, CI=0.55–0.89 → log(0.70) ≈ -0.3567; se ≈ (log(0.89) - log(0.55)) / 3.91993
    eff = es.hazard_ratio_from_ci(hr=0.70, hr_ci_low=0.55, hr_ci_high=0.89)
    assert eff.yi == pytest.approx(math.log(0.70), abs=1e-4)
    expected_se = (math.log(0.89) - math.log(0.55)) / (2 * 1.959964)
    assert eff.se == pytest.approx(expected_se, abs=1e-3)


def test_correlation_fisher_z_transform():
    eff = es.correlation_fisher_z(r=0.5, n=30)
    # z = atanh(0.5) ≈ 0.549306
    assert eff.yi == pytest.approx(math.atanh(0.5), abs=1e-6)
    assert eff.vi == pytest.approx(1 / 27, abs=1e-6)


def test_back_transform_or_exp():
    assert es.back_transform("or", math.log(2.25)) == pytest.approx(2.25, abs=1e-6)
    assert es.back_transform("rr", math.log(1.5)) == pytest.approx(1.5, abs=1e-6)
    assert es.back_transform("hr", math.log(0.7)) == pytest.approx(0.7, abs=1e-6)
    assert es.back_transform("md", 2.0) == pytest.approx(2.0)
    assert es.back_transform("smd", 0.5) == pytest.approx(0.5)
    # Fisher-z back to r
    assert es.back_transform("r", math.atanh(0.5)) == pytest.approx(0.5, abs=1e-6)
