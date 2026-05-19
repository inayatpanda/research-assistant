"""Phase 14 (MP14) — GRADE certainty derivation unit tests."""
from __future__ import annotations

import pytest

from research_api.services.review.grade import compute_certainty


_NO_DOWNGRADES = {
    "risk_of_bias": "not_serious",
    "inconsistency": "not_serious",
    "indirectness": "not_serious",
    "imprecision": "not_serious",
    "publication_bias": "not_serious",
}
_NO_UPGRADES = {
    "large_effect": "none",
    "dose_response": "none",
    "confounders_against": "none",
}


def test_rct_baseline_is_high():
    assert compute_certainty("high", _NO_DOWNGRADES, _NO_UPGRADES) == "high"


def test_observational_baseline_is_low():
    assert compute_certainty("low", _NO_DOWNGRADES, _NO_UPGRADES) == "low"


def test_one_serious_downgrade_drops_one_band():
    downs = dict(_NO_DOWNGRADES, **{"risk_of_bias": "serious"})
    assert compute_certainty("high", downs, _NO_UPGRADES) == "moderate"


def test_two_serious_downgrades_drop_two_bands():
    downs = dict(
        _NO_DOWNGRADES,
        risk_of_bias="serious",
        inconsistency="serious",
    )
    assert compute_certainty("high", downs, _NO_UPGRADES) == "low"


def test_very_serious_drops_two_bands_alone():
    downs = dict(_NO_DOWNGRADES, imprecision="very_serious")
    assert compute_certainty("high", downs, _NO_UPGRADES) == "low"


def test_max_downgrades_floor_at_very_low():
    downs = {k: "very_serious" for k in _NO_DOWNGRADES}
    assert compute_certainty("high", downs, _NO_UPGRADES) == "very_low"


def test_upgrade_when_no_downgrade_lifts_low_to_moderate():
    ups = dict(_NO_UPGRADES, large_effect="present")
    assert compute_certainty("low", _NO_DOWNGRADES, ups) == "moderate"


def test_large_effect_two_can_lift_low_to_high():
    ups = dict(_NO_UPGRADES, large_effect="large")
    assert compute_certainty("low", _NO_DOWNGRADES, ups) == "high"


def test_other_upgrades_cap_at_plus_one_each():
    ups = dict(
        _NO_UPGRADES,
        dose_response="present",
        confounders_against="present",
    )
    assert compute_certainty("low", _NO_DOWNGRADES, ups) == "high"


def test_upgrades_ignored_when_downgrade_present():
    downs = dict(_NO_DOWNGRADES, risk_of_bias="serious")
    ups = dict(_NO_UPGRADES, large_effect="large")
    # base 4 + (-1) downgrade → 3 (moderate); upgrades clamped away.
    assert compute_certainty("high", downs, ups) == "moderate"


def test_high_cannot_exceed_high_even_with_upgrades():
    ups = dict(_NO_UPGRADES, large_effect="large")
    assert compute_certainty("high", _NO_DOWNGRADES, ups) == "high"


def test_invalid_starting_certainty_raises():
    with pytest.raises(ValueError):
        compute_certainty("medium", _NO_DOWNGRADES, _NO_UPGRADES)  # type: ignore[arg-type]


def test_invalid_downgrade_level_raises():
    with pytest.raises(ValueError):
        compute_certainty("high", {"risk_of_bias": "kinda"}, _NO_UPGRADES)


def test_missing_keys_treated_as_neutral():
    # Empty dicts → no deltas → starting band preserved.
    assert compute_certainty("high", {}, {}) == "high"
    assert compute_certainty("low", {}, {}) == "low"
