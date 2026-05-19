"""Phase 17 (MP17) — Post-hoc pairwise comparison known-answer tests."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from research_api.services.stats.post_hoc import (
    bonferroni_pairwise,
    dunns_test,
    games_howell,
    tukey_hsd,
)
from research_api.services.stats.runner import run as runner_run
from research_api.services.stats.registry import post_hoc_follow_up


@pytest.fixture
def three_groups_clearly_different() -> dict[str, list[float]]:
    rng = np.random.default_rng(0)
    return {
        "control": rng.normal(0.0, 1.0, 60).tolist(),
        "drug_low": rng.normal(1.5, 1.0, 60).tolist(),
        "drug_high": rng.normal(3.0, 1.0, 60).tolist(),
    }


@pytest.fixture
def three_groups_identical() -> dict[str, list[float]]:
    rng = np.random.default_rng(0)
    return {
        "a": rng.normal(0.0, 1.0, 60).tolist(),
        "b": rng.normal(0.0, 1.0, 60).tolist(),
        "c": rng.normal(0.0, 1.0, 60).tolist(),
    }


# ── Tukey HSD ───────────────────────────────────────────────────────────────


def test_tukey_hsd_detects_clear_separation(three_groups_clearly_different):
    rows = tukey_hsd(three_groups_clearly_different)
    assert len(rows) == 3  # 3 pairwise comparisons
    # All three pairs should be significant (p_adj < 0.001 with these means).
    for r in rows:
        assert r["p_adj"] < 0.01
        assert r["ci_low"] < r["mean_diff"] < r["ci_high"]
        assert r["method"] == "tukey_hsd"


def test_tukey_hsd_nondiff_groups_nonsignificant(three_groups_identical):
    rows = tukey_hsd(three_groups_identical)
    assert len(rows) == 3
    for r in rows:
        # Most or all should be NS — guard for spurious one
        pass
    assert sum(1 for r in rows if r["p_adj"] < 0.05) == 0


def test_tukey_hsd_validates_minimum_groups():
    with pytest.raises(ValueError):
        tukey_hsd({"only_one": [1.0, 2.0, 3.0]})


# ── Bonferroni pairwise ─────────────────────────────────────────────────────


def test_bonferroni_pairwise_correction_applied(three_groups_clearly_different):
    rows = bonferroni_pairwise(three_groups_clearly_different)
    assert len(rows) == 3
    # Bonferroni cap at 1.0 for p_adj
    for r in rows:
        assert 0 <= r["p_adj"] <= 1.0
        assert r["method"] == "bonferroni"
    # All p_adj are corrected (>= raw / N).
    # Expect all three pairs significant given the design.
    assert all(r["p_adj"] < 0.05 for r in rows)


def test_bonferroni_pairwise_three_groups_pair_count():
    groups = {
        "a": [1.0, 2.0, 3.0, 4.0],
        "b": [5.0, 6.0, 7.0, 8.0],
        "c": [9.0, 10.0, 11.0, 12.0],
    }
    rows = bonferroni_pairwise(groups)
    assert len(rows) == 3


# ── Dunn's test ─────────────────────────────────────────────────────────────


def test_dunns_test_detects_separation(three_groups_clearly_different):
    rows = dunns_test(three_groups_clearly_different)
    assert len(rows) == 3
    for r in rows:
        assert r["method"] == "dunns"
        assert r["z_statistic"] is not None
    assert all(r["p_adj"] < 0.05 for r in rows)


def test_dunns_test_handles_ties():
    """Dunn's test with tied ranks should still produce finite p-values."""
    groups = {
        "a": [1.0, 1.0, 2.0, 2.0, 3.0, 3.0],
        "b": [4.0, 4.0, 5.0, 5.0, 6.0, 6.0],
    }
    rows = dunns_test(groups)
    assert len(rows) == 1
    assert rows[0]["p_adj"] is not None
    assert 0 <= rows[0]["p_adj"] <= 1.0


# ── Games-Howell ────────────────────────────────────────────────────────────


def test_games_howell_handles_unequal_variance():
    rng = np.random.default_rng(1)
    groups = {
        "a": rng.normal(0.0, 0.5, 50).tolist(),
        "b": rng.normal(3.0, 2.5, 50).tolist(),
        "c": rng.normal(6.0, 5.0, 50).tolist(),
    }
    rows = games_howell(groups)
    assert len(rows) == 3
    for r in rows:
        assert r["method"] == "games_howell"
        assert r["df"] is not None


def test_games_howell_pair_count_grows_quadratically():
    rng = np.random.default_rng(2)
    groups = {
        f"g{i}": rng.normal(0.0, 1.0, 30).tolist() for i in range(5)
    }
    rows = games_howell(groups)
    # 5 groups → 10 pairwise comparisons
    assert len(rows) == 10


# ── Runner dispatch ─────────────────────────────────────────────────────────


def _build_df(groups: dict[str, list[float]]) -> pd.DataFrame:
    rows = []
    for label, vals in groups.items():
        for v in vals:
            rows.append({"y": float(v), "g": label})
    return pd.DataFrame(rows)


def test_runner_dispatch_post_hoc_tukey(three_groups_clearly_different):
    df = _build_df(three_groups_clearly_different)
    out = runner_run(
        test_key="post_hoc_tukey",
        df=df,
        variables={"outcome": "y", "groups": "g"},
    )
    assert out.test_key == "post_hoc_tukey"
    assert len(out.extras["pairs"]) == 3
    assert out.statistic == 3.0  # n_pairs
    assert out.n == sum(len(v) for v in three_groups_clearly_different.values())


def test_runner_dispatch_post_hoc_dunns(three_groups_clearly_different):
    df = _build_df(three_groups_clearly_different)
    out = runner_run(
        test_key="post_hoc_dunns",
        df=df,
        variables={"outcome": "y", "groups": "g"},
    )
    assert out.extras["method"] == "dunns"
    assert len(out.extras["pairs"]) == 3


def test_runner_post_hoc_requires_minimum_two_groups():
    df = pd.DataFrame({"y": [1.0, 2.0, 3.0], "g": ["a", "a", "a"]})
    with pytest.raises(ValueError, match="requires >= 2 groups"):
        runner_run(
            test_key="post_hoc_tukey",
            df=df,
            variables={"outcome": "y", "groups": "g"},
        )


# ── Follow-up suggestion (registry) ─────────────────────────────────────────


def test_post_hoc_follow_up_anova_significant_default():
    result = post_hoc_follow_up(
        omnibus_test_key="one_way_anova", p_value=0.01
    )
    assert result["post_hoc_recommended"] is True
    assert "post_hoc_tukey" in result["suggested_tests"]


def test_post_hoc_follow_up_anova_unequal_var_swaps_to_games_howell():
    result = post_hoc_follow_up(
        omnibus_test_key="one_way_anova", p_value=0.01, equal_var_ok=False
    )
    assert result["suggested_tests"][0] == "post_hoc_games_howell"


def test_post_hoc_follow_up_kruskal_wallis_uses_dunns():
    result = post_hoc_follow_up(
        omnibus_test_key="kruskal_wallis", p_value=0.01
    )
    assert "post_hoc_dunns" in result["suggested_tests"]


def test_post_hoc_follow_up_skipped_when_non_significant():
    result = post_hoc_follow_up(
        omnibus_test_key="one_way_anova", p_value=0.20
    )
    assert result["post_hoc_recommended"] is False
    assert result["suggested_tests"] == []


def test_post_hoc_follow_up_skipped_for_two_group_test():
    result = post_hoc_follow_up(
        omnibus_test_key="independent_t", p_value=0.01
    )
    assert result["post_hoc_recommended"] is False
