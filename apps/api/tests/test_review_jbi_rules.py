"""Phase 19 (MP19) — JBI catalogue + derive_overall_jbi."""
from __future__ import annotations

import pytest

from research_api.services.review.jbi_rules import (
    JBI_CATALOGUE,
    derive_overall_jbi,
)
from research_api.services.review.rob_rules import (
    CATALOGUE,
    derive_overall,
    get_catalogue,
)


def test_catalogue_has_seven_jbi_tools():
    expected = {
        "jbi_case_series",
        "jbi_case_report",
        "jbi_cohort",
        "jbi_cross_sectional",
        "jbi_quasi_experimental",
        "jbi_diagnostic_accuracy",
        "jbi_prevalence",
    }
    assert set(JBI_CATALOGUE.keys()) == expected


def test_each_jbi_tool_has_correct_item_count():
    counts = {
        "jbi_case_series": 10,
        "jbi_case_report": 8,
        "jbi_cohort": 11,
        "jbi_cross_sectional": 8,
        "jbi_quasi_experimental": 9,
        "jbi_diagnostic_accuracy": 10,
        "jbi_prevalence": 9,
    }
    for key, expected_count in counts.items():
        tool = JBI_CATALOGUE[key]
        assert len(tool.domains) == expected_count, key


def test_jbi_tools_registered_in_main_catalogue():
    cat = get_catalogue()
    for key in JBI_CATALOGUE:
        assert key in cat
    # And after lazy loading the module-level CATALOGUE has them too.
    for key in JBI_CATALOGUE:
        assert key in CATALOGUE


def test_derive_low_at_70_percent_yes():
    # Cohort = 11 items; 8 yes + 3 no → 8/11 ≈ 72.7% → low
    answers = {f"co_{i}": ("yes" if i <= 8 else "no") for i in range(1, 12)}
    assert derive_overall_jbi("jbi_cohort", answers) == "low"


def test_derive_moderate_band():
    # Case Series 10 items; 6 yes + 4 no → 60% → moderate
    answers = {f"cs_{i}": ("yes" if i <= 6 else "no") for i in range(1, 11)}
    assert derive_overall_jbi("jbi_case_series", answers) == "moderate"


def test_derive_high_band():
    # Diagnostic 10 items; 4 yes + 6 no → 40% → high
    answers = {f"dta_{i}": ("yes" if i <= 4 else "no") for i in range(1, 11)}
    assert derive_overall_jbi("jbi_diagnostic_accuracy", answers) == "high"


def test_derive_unclear_when_all_unclear():
    answers = {f"pv_{i}": "unclear" for i in range(1, 10)}
    assert derive_overall_jbi("jbi_prevalence", answers) == "unclear"


def test_na_answers_excluded_from_yes_percentage():
    # Quasi-experimental 9 items; 5 yes + 1 no + 3 na → 5/6 ≈ 83% → low
    answers = {
        "qe_1": "yes", "qe_2": "yes", "qe_3": "yes", "qe_4": "yes", "qe_5": "yes",
        "qe_6": "no", "qe_7": "na", "qe_8": "na", "qe_9": "na",
    }
    assert derive_overall_jbi("jbi_quasi_experimental", answers) == "low"


def test_invalid_answer_raises():
    with pytest.raises(ValueError):
        derive_overall_jbi("jbi_cohort", {"co_1": "maybe"})


def test_unknown_tool_raises():
    with pytest.raises(ValueError):
        derive_overall_jbi("rob_unknown", {})


def test_unknown_domain_raises():
    with pytest.raises(ValueError):
        derive_overall_jbi("jbi_cohort", {"made_up": "yes"})


def test_derive_overall_dispatch_picks_jbi():
    # rob_rules.derive_overall must dispatch JBI keys to derive_overall_jbi.
    answers = {f"cs_{i}": "yes" for i in range(1, 11)}
    assert derive_overall("jbi_case_series", answers) == "low"
