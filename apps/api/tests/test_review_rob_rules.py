from __future__ import annotations

import pytest

from research_api.services.review.rob_rules import (
    AMSTAR2_UNIFIED_MAPPING,
    CATALOGUE,
    Domain,
    Tool,
    derive_overall,
    select_tool_for_design,
)


def test_catalogue_has_four_tools():
    assert set(CATALOGUE.keys()) == {"rob2", "robins_i", "nos", "amstar2"}
    for tool in CATALOGUE.values():
        assert isinstance(tool, Tool)
        assert tool.label
        assert tool.domains


def test_rob2_has_five_domains_with_questions():
    tool = CATALOGUE["rob2"]
    keys = [d.key for d in tool.domains]
    assert keys == ["randomisation", "deviations", "missing_outcome", "measurement", "reporting"]
    for d in tool.domains:
        assert d.question
        assert set(d.answers) >= {"low", "some_concerns", "high", "unclear"}


def test_robinsi_has_seven_domains_with_questions():
    tool = CATALOGUE["robins_i"]
    keys = [d.key for d in tool.domains]
    assert keys == [
        "confounding", "selection", "classification",
        "deviations", "missing_data", "measurement", "reporting",
    ]
    for d in tool.domains:
        assert d.question
        assert set(d.answers) >= {"low", "moderate", "serious", "critical", "no_information"}


def test_nos_has_three_groups():
    tool = CATALOGUE["nos"]
    keys = [d.key for d in tool.domains]
    assert keys == ["selection", "comparability", "outcome"]
    for d in tool.domains:
        assert d.question


def test_amstar2_has_sixteen_items():
    tool = CATALOGUE["amstar2"]
    assert len(tool.domains) == 16
    for d in tool.domains:
        assert d.question
        assert set(d.answers) == {"yes", "partial_yes", "no"}


@pytest.mark.parametrize("tool_key", ["rob2", "robins_i", "nos", "amstar2"])
def test_every_domain_has_at_least_one_answer_and_a_nonempty_question(tool_key):
    tool = CATALOGUE[tool_key]
    for d in tool.domains:
        assert isinstance(d, Domain)
        assert d.question.strip()
        assert len(d.answers) >= 1


@pytest.mark.parametrize(
    "answers,expected",
    [
        ({"randomisation": "low", "deviations": "low", "missing_outcome": "low",
          "measurement": "low", "reporting": "low"}, "low"),
        ({"randomisation": "low", "deviations": "low", "missing_outcome": "some_concerns",
          "measurement": "low", "reporting": "low"}, "some_concerns"),
        ({"randomisation": "low", "deviations": "low", "missing_outcome": "low",
          "measurement": "high", "reporting": "low"}, "high"),
        ({"randomisation": "unclear", "deviations": "low", "missing_outcome": "low",
          "measurement": "low", "reporting": "low"}, "unclear"),
        ({"randomisation": "unclear", "deviations": "high", "missing_outcome": "low",
          "measurement": "low", "reporting": "low"}, "high"),
        ({"randomisation": "unclear", "deviations": "some_concerns", "missing_outcome": "low",
          "measurement": "low", "reporting": "low"}, "some_concerns"),
    ],
)
def test_overall_from_worst_rob2_table(answers, expected):
    assert derive_overall("rob2", answers) == expected


@pytest.mark.parametrize(
    "answers,expected",
    [
        ({k: "low" for k in
          ["confounding", "selection", "classification", "deviations",
           "missing_data", "measurement", "reporting"]}, "low"),
        ({"confounding": "moderate", "selection": "low", "classification": "low",
          "deviations": "low", "missing_data": "low", "measurement": "low",
          "reporting": "low"}, "some_concerns"),
        ({"confounding": "low", "selection": "low", "classification": "serious",
          "deviations": "low", "missing_data": "low", "measurement": "low",
          "reporting": "low"}, "high"),
        ({"confounding": "critical", "selection": "low", "classification": "low",
          "deviations": "low", "missing_data": "low", "measurement": "low",
          "reporting": "low"}, "critical"),
        ({"confounding": "no_information", "selection": "low", "classification": "low",
          "deviations": "low", "missing_data": "low", "measurement": "low",
          "reporting": "low"}, "unclear"),
        ({"confounding": "no_information", "selection": "serious", "classification": "low",
          "deviations": "low", "missing_data": "low", "measurement": "low",
          "reporting": "low"}, "high"),
    ],
)
def test_overall_from_worst_robinsi_table(answers, expected):
    assert derive_overall("robins_i", answers) == expected


@pytest.mark.parametrize(
    "yes_count,expected",
    [
        (9, "low"),
        (8, "low"),
        (7, "low"),
        (6, "some_concerns"),
        (5, "some_concerns"),
        (4, "high"),
        (3, "high"),
        (0, "high"),
    ],
)
def test_overall_from_nos_star_count(yes_count, expected):
    answers = {}
    keys = [
        "sel_1", "sel_2", "sel_3", "sel_4",
        "comp_1", "comp_2",
        "out_1", "out_2", "out_3",
    ]
    for i, k in enumerate(keys):
        answers[k] = "yes" if i < yes_count else "no"
    assert derive_overall("nos", answers) == expected


@pytest.mark.parametrize(
    "critical_weaknesses,noncritical_weaknesses,expected",
    [
        (0, 0, "low"),
        (0, 1, "low"),
        (0, 2, "some_concerns"),
        (1, 0, "high"),
        (1, 3, "high"),
        (2, 0, "critical"),
        (3, 5, "critical"),
    ],
)
def test_overall_from_amstar2_critical_count(
    critical_weaknesses, noncritical_weaknesses, expected
):
    tool = CATALOGUE["amstar2"]
    critical_keys = [d.key for d in tool.domains if d.critical]
    noncritical_keys = [d.key for d in tool.domains if not d.critical]
    answers = {k: "yes" for d in tool.domains for k in [d.key]}
    for i in range(critical_weaknesses):
        answers[critical_keys[i]] = "no"
    for i in range(noncritical_weaknesses):
        answers[noncritical_keys[i]] = "no"
    assert derive_overall("amstar2", answers) == expected


def test_amstar2_vocabulary_maps_to_unified():
    assert AMSTAR2_UNIFIED_MAPPING == {
        "high": "low",
        "moderate": "some_concerns",
        "low": "high",
        "critical_low": "critical",
    }


def test_tool_applies_to_includes_correct_study_designs():
    assert "RCT" in CATALOGUE["rob2"].applies_to
    assert "cohort" in CATALOGUE["robins_i"].applies_to
    assert "case_control" in CATALOGUE["robins_i"].applies_to
    assert "cohort" in CATALOGUE["nos"].applies_to
    assert "systematic_review" in CATALOGUE["amstar2"].applies_to
    assert "meta_analysis" in CATALOGUE["amstar2"].applies_to


def test_select_tool_for_design_rct():
    tool = select_tool_for_design("RCT")
    assert tool is not None
    assert tool.key == "rob2"


def test_select_tool_for_design_cohort():
    tool = select_tool_for_design("cohort")
    assert tool is not None
    assert tool.key in {"robins_i", "nos"}


def test_select_tool_for_design_systematic_review():
    tool = select_tool_for_design("systematic_review")
    assert tool is not None
    assert tool.key == "amstar2"


def test_select_tool_for_design_unknown():
    assert select_tool_for_design("not_a_design") is None


def test_unknown_answer_raises_value_error():
    with pytest.raises(ValueError):
        derive_overall("rob2", {
            "randomisation": "totally_invalid",
            "deviations": "low",
            "missing_outcome": "low",
            "measurement": "low",
            "reporting": "low",
        })


def test_unknown_tool_raises_value_error():
    with pytest.raises(ValueError):
        derive_overall("not_a_tool", {})
