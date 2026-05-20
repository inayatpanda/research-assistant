"""Phase 18 (MP18) — Utility value-set tests."""
from __future__ import annotations

import pytest

from research_api.services.economics.utility_value_sets import (
    apply_value_set,
    catalogue,
)


def _eq5d_profile(*levels: int) -> dict[str, int]:
    keys = ("mobility", "self_care", "usual_activities", "pain", "anxiety")
    if len(levels) != 5:
        raise ValueError("need 5 levels")
    return dict(zip(keys, levels))


def test_eq5d_3l_uk_perfect_health_is_one():
    assert apply_value_set("EQ5D_3L_UK", _eq5d_profile(1, 1, 1, 1, 1)) == pytest.approx(1.0)


def test_eq5d_3l_uk_worst_state_dolan_1997():
    """Dolan 1997 worst state (33333) = -0.594.

    Computation:
      1.0 - 0.081 (const) - (0.314+0.214+0.094+0.386+0.236) - 0.269 (N3)
      = 1.0 - 0.081 - 1.244 - 0.269 = -0.594.
    """
    u = apply_value_set("EQ5D_3L_UK", _eq5d_profile(3, 3, 3, 3, 3))
    assert u == pytest.approx(-0.594, abs=1e-6)


def test_eq5d_3l_uk_one_problem_no_n3():
    """Profile 21111 → 1 - 0.081 - 0.069 = 0.850 (no N3 because no level=3)."""
    u = apply_value_set("EQ5D_3L_UK", _eq5d_profile(2, 1, 1, 1, 1))
    assert u == pytest.approx(0.850, abs=1e-6)


def test_eq5d_5l_uk_perfect_health_is_one():
    assert apply_value_set("EQ5D_5L_UK", _eq5d_profile(1, 1, 1, 1, 1)) == pytest.approx(1.0)


def test_eq5d_5l_uk_one_level2_problem_subtracts_decrement():
    """5L profile 21111: 1.0 - 0.058 = 0.942."""
    u = apply_value_set("EQ5D_5L_UK", _eq5d_profile(2, 1, 1, 1, 1))
    assert u == pytest.approx(0.942, abs=1e-6)


def test_sf6d_perfect_health_is_one():
    profile = {
        "physical_functioning": 1,
        "role_limitations": 1,
        "social_functioning": 1,
        "pain": 1,
        "mental_health": 1,
        "vitality": 1,
    }
    assert apply_value_set("SF6D", profile) == pytest.approx(1.0)


def test_direct_value_set_passes_through():
    assert apply_value_set("direct", {"utility": 0.72}) == pytest.approx(0.72)


def test_catalogue_lists_all_value_sets():
    keys = {entry["key"] for entry in catalogue()}
    assert {"EQ5D_3L_UK", "EQ5D_5L_UK", "EQ5D_Y_DUTCH", "SF6D", "direct"} <= keys


def test_unknown_value_set_errors():
    with pytest.raises(ValueError, match="unknown"):
        apply_value_set("MADE_UP", {})  # type: ignore[arg-type]


def test_eq5d_3l_uk_invalid_level_errors():
    with pytest.raises(ValueError, match="level"):
        apply_value_set("EQ5D_3L_UK", _eq5d_profile(4, 1, 1, 1, 1))
