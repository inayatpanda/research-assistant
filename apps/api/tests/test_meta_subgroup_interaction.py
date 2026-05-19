"""Phase 19 (MP19) — Subgroup Q-between interaction test."""
from __future__ import annotations

import pytest

from research_api.services.meta import effect_sizes as es
from research_api.services.meta.heterogeneity import heterogeneity
from research_api.services.meta.subgroup_interaction import subgroup_q_between


def _eff(yi: float, se: float) -> es.Effect:
    return es.Effect(yi=yi, se=se, vi=se * se, metric="md")


def test_subgroup_q_between_matches_q_total_minus_q_within():
    # Three subgroups, each with 2-3 studies
    g_a = [_eff(0.10, 0.10), _eff(0.12, 0.10)]
    g_b = [_eff(0.30, 0.10), _eff(0.35, 0.10), _eff(0.32, 0.10)]
    g_c = [_eff(-0.10, 0.10), _eff(-0.08, 0.10)]
    result = subgroup_q_between({"A": g_a, "B": g_b, "C": g_c})

    all_eff = g_a + g_b + g_c
    q_total = heterogeneity(all_eff).q
    q_within = sum(
        heterogeneity(g).q for g in (g_a, g_b, g_c) if len(g) >= 2
    )
    expected = max(0.0, q_total - q_within)
    assert result.df == 2  # 3 subgroups − 1
    assert result.q_between == pytest.approx(expected, abs=1e-6)
    assert 0.0 <= result.p_interaction <= 1.0


def test_q_between_zero_when_subgroup_means_match():
    g_a = [_eff(0.20, 0.05), _eff(0.20, 0.05)]
    g_b = [_eff(0.20, 0.05), _eff(0.20, 0.05)]
    res = subgroup_q_between({"A": g_a, "B": g_b})
    assert res.q_between == pytest.approx(0.0, abs=1e-6)
    assert res.p_interaction > 0.9


def test_q_between_significant_when_subgroups_diverge():
    # Two subgroups with very different effects; high Q_between → low p.
    g_a = [_eff(0.10, 0.02), _eff(0.12, 0.02), _eff(0.11, 0.02)]
    g_b = [_eff(1.50, 0.02), _eff(1.55, 0.02), _eff(1.52, 0.02)]
    res = subgroup_q_between({"A": g_a, "B": g_b})
    assert res.q_between > 100.0
    assert res.p_interaction < 0.001


def test_subgroup_q_between_needs_two_subgroups():
    g_a = [_eff(0.1, 0.1), _eff(0.2, 0.1)]
    with pytest.raises(ValueError):
        subgroup_q_between({"A": g_a})


def test_empty_subgroups_are_skipped():
    g_a = [_eff(0.1, 0.1), _eff(0.2, 0.1)]
    g_b = [_eff(0.3, 0.1), _eff(0.5, 0.1)]
    # An empty third subgroup must be transparently dropped (still 2 valid)
    res = subgroup_q_between({"A": g_a, "B": g_b, "C": []})
    assert res.df == 1


def test_single_study_subgroups_contribute_zero_q_within():
    # Subgroup with 1 study still counts toward df but has zero Q_within
    g_a = [_eff(0.1, 0.1), _eff(0.2, 0.1)]
    g_b = [_eff(0.5, 0.1)]  # singleton
    res = subgroup_q_between({"A": g_a, "B": g_b})
    assert res.df == 1
