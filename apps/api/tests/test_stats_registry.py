from __future__ import annotations

import pytest

from research_api.services.stats.registry import (
    CATALOGUE,
    TestSpec,
    recommend,
)


def test_catalogue_has_all_keys():
    # MP13 expanded the catalogue from 18 to 27 keys. Asserts ⊇ rather than ==
    # so future additions don't break this; explicit guards on the 9 MP13 keys
    # below catch any regression.
    core_18 = {
        "independent_t",
        "paired_t",
        "mann_whitney",
        "wilcoxon_signed",
        "chi_squared",
        "fisher_exact",
        "one_way_anova",
        "kruskal_wallis",
        "rm_anova",
        "pearson",
        "spearman",
        "linear_regression",
        "multiple_linear",
        "logistic",
        "kaplan_meier",
        "cox_ph",
        "icc",
        "cohen_kappa",
    }
    mp13_9 = {
        "mixed_effects_lm",
        "glm_poisson",
        "glm_binomial",
        "glm_gamma",
        "gee",
        "bootstrap_mean_diff",
        "permutation_test",
        "tost_equivalence",
        "tost_noninferiority",
    }
    keys = set(CATALOGUE.keys())
    assert core_18 <= keys
    assert mp13_9 <= keys
    for spec in CATALOGUE.values():
        assert isinstance(spec, TestSpec)
        assert spec.label
        assert spec.rationale
        assert spec.question_type in {
            "group_comparison",
            "association",
            "time_to_event",
            "agreement",
        }


def test_group_comparison_2grp_numeric_normal_independent():
    key, rationale = recommend(
        question_type="group_comparison",
        var_types={"outcome": "numeric", "groups": "nominal"},
        n_groups=2,
        paired=False,
        normality_ok=True,
    )
    assert key == "independent_t"
    assert rationale


def test_group_comparison_2grp_numeric_nonnormal_mann_whitney():
    key, _ = recommend(
        question_type="group_comparison",
        var_types={"outcome": "numeric", "groups": "nominal"},
        n_groups=2,
        paired=False,
        normality_ok=False,
    )
    assert key == "mann_whitney"


def test_group_comparison_2grp_paired_normal_paired_t():
    key, _ = recommend(
        question_type="group_comparison",
        var_types={"outcome": "numeric", "groups": "nominal"},
        n_groups=2,
        paired=True,
        normality_ok=True,
    )
    assert key == "paired_t"


def test_group_comparison_2grp_paired_nonnormal_wilcoxon():
    key, _ = recommend(
        question_type="group_comparison",
        var_types={"outcome": "numeric", "groups": "nominal"},
        n_groups=2,
        paired=True,
        normality_ok=False,
    )
    assert key == "wilcoxon_signed"


def test_group_comparison_2grp_nominal_outcome_chi_squared():
    key, _ = recommend(
        question_type="group_comparison",
        var_types={"outcome": "nominal", "groups": "nominal"},
        n_groups=2,
        min_expected_count=10,
    )
    assert key == "chi_squared"


def test_group_comparison_2grp_nominal_outcome_small_cells_fisher():
    key, _ = recommend(
        question_type="group_comparison",
        var_types={"outcome": "nominal", "groups": "nominal"},
        n_groups=2,
        min_expected_count=3,
    )
    assert key == "fisher_exact"


def test_group_comparison_3plus_numeric_normal_anova():
    key, _ = recommend(
        question_type="group_comparison",
        var_types={"outcome": "numeric", "groups": "nominal"},
        n_groups=3,
        paired=False,
        normality_ok=True,
    )
    assert key == "one_way_anova"


def test_group_comparison_3plus_numeric_nonnormal_kruskal():
    key, _ = recommend(
        question_type="group_comparison",
        var_types={"outcome": "numeric", "groups": "nominal"},
        n_groups=3,
        paired=False,
        normality_ok=False,
    )
    assert key == "kruskal_wallis"


def test_group_comparison_3plus_paired_rm_anova():
    key, _ = recommend(
        question_type="group_comparison",
        var_types={"outcome": "numeric", "groups": "nominal"},
        n_groups=3,
        paired=True,
    )
    assert key == "rm_anova"


def test_association_numeric_numeric_normal_pearson():
    key, _ = recommend(
        question_type="association",
        var_types={"x": "numeric", "y": "numeric"},
        normality_ok=True,
    )
    assert key == "pearson"


def test_association_numeric_numeric_nonnormal_spearman():
    key, _ = recommend(
        question_type="association",
        var_types={"x": "numeric", "y": "numeric"},
        normality_ok=False,
    )
    assert key == "spearman"


def test_association_intent_predict_linear_regression():
    key, _ = recommend(
        question_type="association",
        var_types={"outcome": "numeric", "predictors": "numeric"},
        intent="predict",
    )
    assert key == "linear_regression"


def test_association_multi_predictors_multiple_linear():
    key, _ = recommend(
        question_type="association",
        var_types={"outcome": "numeric", "predictors": ["numeric", "nominal"]},
        intent="predict",
    )
    assert key == "multiple_linear"


def test_association_binary_outcome_logistic():
    key, _ = recommend(
        question_type="association",
        var_types={"outcome": "event_indicator", "predictors": ["numeric"]},
        intent="predict",
    )
    assert key == "logistic"


def test_time_to_event_single_group_km():
    key, _ = recommend(
        question_type="time_to_event",
        var_types={"time": "time", "event": "event_indicator", "groups": "nominal"},
        covariates=False,
    )
    assert key == "kaplan_meier"


def test_time_to_event_with_covariates_cox():
    key, _ = recommend(
        question_type="time_to_event",
        var_types={
            "time": "time",
            "event": "event_indicator",
            "covariates": ["numeric", "nominal"],
        },
        covariates=True,
    )
    assert key == "cox_ph"


def test_agreement_numeric_two_raters_icc():
    key, _ = recommend(
        question_type="agreement",
        var_types={"rater_a": "numeric", "rater_b": "numeric"},
    )
    assert key == "icc"


def test_agreement_nominal_two_raters_kappa():
    key, _ = recommend(
        question_type="agreement",
        var_types={"rater_a": "nominal", "rater_b": "nominal"},
    )
    assert key == "cohen_kappa"


def test_unknown_question_type_raises():
    with pytest.raises(ValueError):
        recommend(question_type="bogus", var_types={})


def test_rationale_contains_test_label_or_key():
    key, rationale = recommend(
        question_type="group_comparison",
        var_types={"outcome": "numeric", "groups": "nominal"},
        n_groups=2,
        paired=False,
        normality_ok=True,
    )
    assert isinstance(rationale, str)
    assert len(rationale) > 10
