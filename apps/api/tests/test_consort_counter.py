"""Phase 8.7 — CONSORT counter unit tests."""
from __future__ import annotations

from research_api.services.consort.counter import derive_flow


def test_derive_flow_warns_when_excluded_reasons_dont_sum() -> None:
    flow = derive_flow({
        "enrollment_assessed": 200,
        "enrollment_excluded": 50,
        "enrollment_excluded_reasons": {"Declined": 30, "Ineligible": 19},  # sum = 49
        "randomised": 150,
    })
    assert any("exclusion reasons" in w for w in flow.warnings)


def test_derive_flow_warns_when_assessed_minus_excluded_neq_randomised() -> None:
    flow = derive_flow({
        "enrollment_assessed": 200,
        "enrollment_excluded": 50,
        "randomised": 140,  # 200-50 = 150 != 140
    })
    assert any("randomised" in w for w in flow.warnings)


def test_derive_flow_warns_when_arms_dont_sum_to_randomised() -> None:
    flow = derive_flow({
        "randomised": 150,
        "allocated_intervention": 80,
        "allocated_control": 80,
    })
    assert any("allocated_intervention + allocated_control" in w for w in flow.warnings)


def test_derive_flow_warns_when_received_exceeds_allocated() -> None:
    flow = derive_flow({
        "allocated_intervention": 50,
        "intervention_received": 60,
    })
    assert any("intervention_received" in w for w in flow.warnings)


def test_derive_flow_handles_all_nulls() -> None:
    flow = derive_flow({})
    assert flow.warnings == []
    assert flow.assessed is None
    assert flow.allocated == {"intervention": None, "control": None}


def test_derive_flow_clean_input_no_warnings() -> None:
    flow = derive_flow({
        "enrollment_assessed": 200,
        "enrollment_excluded": 50,
        "enrollment_excluded_reasons": {"Declined": 30, "Ineligible": 20},
        "randomised": 150,
        "allocated_intervention": 75,
        "allocated_control": 75,
        "intervention_received": 75,
        "control_received": 75,
    })
    assert flow.warnings == []
