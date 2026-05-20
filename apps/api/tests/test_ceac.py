"""Phase 18 (MP18) — CEAC construction tests."""
from __future__ import annotations

import pytest

from research_api.services.economics.ceac import build_ceac


def test_ceac_all_reps_dominant_gives_full_curve_at_one():
    """If every bootstrap rep has dQALY > 0 and dCost < 0, the intervention
    dominates at every WTP, so P(cost-effective) = 1.0 across the grid.
    """
    plane = [{"dCost": -100.0, "dQALY": 0.05} for _ in range(50)]
    curve = build_ceac(plane, wtp_range=(0, 50000, 10000))
    assert len(curve) == 6
    for p in curve:
        assert p["prob_costeffective"] == pytest.approx(1.0)
        assert 0 <= p["wtp"] <= 50000


def test_ceac_monotone_increasing_with_wtp_in_NE():
    """For reps in the NE quadrant with varying ICERs, CEAC is non-decreasing
    in WTP (higher WTP = more reps clear the threshold).
    """
    # ICERs 10k, 20k, 30k, 40k, 50k.
    plane = [
        {"dCost": 1000.0, "dQALY": 0.1},   # ICER 10k
        {"dCost": 2000.0, "dQALY": 0.1},   # ICER 20k
        {"dCost": 3000.0, "dQALY": 0.1},   # ICER 30k
        {"dCost": 4000.0, "dQALY": 0.1},   # ICER 40k
        {"dCost": 5000.0, "dQALY": 0.1},   # ICER 50k
    ]
    curve = build_ceac(plane, wtp_range=(0, 60000, 10000))
    probs = [p["prob_costeffective"] for p in curve]
    # WTP=0 → none cost-effective.
    assert probs[0] == pytest.approx(0.0)
    # WTP=10k → strictly greater than threshold? No, NMB > 0 strict; with
    # ICER 10k at WTP 10k → NMB = 0 → NOT counted. So still 0.0.
    assert probs[1] == pytest.approx(0.0)
    # WTP=20k → only ICER 10k clears (NMB=1000 > 0). So 0.2.
    assert probs[2] == pytest.approx(0.2)
    # Each step up by 10k captures one more rep.
    for i in range(1, len(probs)):
        assert probs[i] >= probs[i - 1]


def test_ceac_empty_plane_returns_empty_curve():
    assert build_ceac([], wtp_range=(0, 50000, 10000)) == []


def test_ceac_step_must_be_positive():
    with pytest.raises(ValueError, match="step"):
        build_ceac([{"dCost": 1.0, "dQALY": 0.01}], wtp_range=(0, 10, 0))
