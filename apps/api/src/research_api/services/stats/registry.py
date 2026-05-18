from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from research_api.schemas.analysis import QuestionType, TestKey


@dataclass(frozen=True)
class TestSpec:
    key: str
    label: str
    question_type: str
    requires: dict[str, str]
    n_groups: int | None
    paired: bool
    nonparametric: bool
    rationale: str


TestSpec.__test__ = False  # type: ignore[attr-defined]


CATALOGUE: dict[str, TestSpec] = {
    "independent_t": TestSpec(
        key="independent_t",
        label="Independent samples t-test",
        question_type="group_comparison",
        requires={"outcome": "numeric", "groups": "nominal"},
        n_groups=2,
        paired=False,
        nonparametric=False,
        rationale="Comparing a numeric outcome between two independent groups with approximately normal distributions.",
    ),
    "paired_t": TestSpec(
        key="paired_t",
        label="Paired t-test",
        question_type="group_comparison",
        requires={"outcome": "numeric", "groups": "nominal"},
        n_groups=2,
        paired=True,
        nonparametric=False,
        rationale="Comparing two paired/repeated measurements per subject with approximately normal within-pair differences.",
    ),
    "mann_whitney": TestSpec(
        key="mann_whitney",
        label="Mann-Whitney U test",
        question_type="group_comparison",
        requires={"outcome": "numeric", "groups": "nominal"},
        n_groups=2,
        paired=False,
        nonparametric=True,
        rationale="Two-group comparison where the numeric outcome does not meet the normality assumption.",
    ),
    "wilcoxon_signed": TestSpec(
        key="wilcoxon_signed",
        label="Wilcoxon signed-rank test",
        question_type="group_comparison",
        requires={"outcome": "numeric", "groups": "nominal"},
        n_groups=2,
        paired=True,
        nonparametric=True,
        rationale="Paired comparison with non-normal differences; rank-based alternative to the paired t-test.",
    ),
    "chi_squared": TestSpec(
        key="chi_squared",
        label="Chi-squared test of independence",
        question_type="group_comparison",
        requires={"outcome": "nominal", "groups": "nominal"},
        n_groups=2,
        paired=False,
        nonparametric=True,
        rationale="Comparing categorical proportions between groups when all expected cell counts are reasonable.",
    ),
    "fisher_exact": TestSpec(
        key="fisher_exact",
        label="Fisher's exact test",
        question_type="group_comparison",
        requires={"outcome": "nominal", "groups": "nominal"},
        n_groups=2,
        paired=False,
        nonparametric=True,
        rationale="Comparing categorical proportions when some expected cell counts are small (typically <5).",
    ),
    "one_way_anova": TestSpec(
        key="one_way_anova",
        label="One-way ANOVA",
        question_type="group_comparison",
        requires={"outcome": "numeric", "groups": "nominal"},
        n_groups=None,
        paired=False,
        nonparametric=False,
        rationale="Comparing a numeric outcome across three or more independent groups under normality.",
    ),
    "kruskal_wallis": TestSpec(
        key="kruskal_wallis",
        label="Kruskal-Wallis H test",
        question_type="group_comparison",
        requires={"outcome": "numeric", "groups": "nominal"},
        n_groups=None,
        paired=False,
        nonparametric=True,
        rationale="Three-plus group comparison without the normality assumption; rank-based alternative to ANOVA.",
    ),
    "rm_anova": TestSpec(
        key="rm_anova",
        label="Repeated-measures ANOVA",
        question_type="group_comparison",
        requires={"outcome": "numeric", "groups": "nominal"},
        n_groups=None,
        paired=True,
        nonparametric=False,
        rationale="Comparing a numeric outcome across three or more repeated measurements within subject.",
    ),
    "pearson": TestSpec(
        key="pearson",
        label="Pearson correlation",
        question_type="association",
        requires={"x": "numeric", "y": "numeric"},
        n_groups=None,
        paired=False,
        nonparametric=False,
        rationale="Linear association between two numeric variables under approximate normality.",
    ),
    "spearman": TestSpec(
        key="spearman",
        label="Spearman rank correlation",
        question_type="association",
        requires={"x": "numeric", "y": "numeric"},
        n_groups=None,
        paired=False,
        nonparametric=True,
        rationale="Monotonic association between two numeric variables without the normality assumption.",
    ),
    "linear_regression": TestSpec(
        key="linear_regression",
        label="Simple linear regression",
        question_type="association",
        requires={"outcome": "numeric", "predictors": "numeric"},
        n_groups=None,
        paired=False,
        nonparametric=False,
        rationale="Predicting a numeric outcome from a single numeric predictor.",
    ),
    "multiple_linear": TestSpec(
        key="multiple_linear",
        label="Multiple linear regression",
        question_type="association",
        requires={"outcome": "numeric", "predictors": "mixed"},
        n_groups=None,
        paired=False,
        nonparametric=False,
        rationale="Predicting a numeric outcome from two or more predictors that may be numeric or categorical.",
    ),
    "logistic": TestSpec(
        key="logistic",
        label="Logistic regression",
        question_type="association",
        requires={"outcome": "event_indicator", "predictors": "mixed"},
        n_groups=None,
        paired=False,
        nonparametric=False,
        rationale="Predicting a binary outcome from one or more predictors.",
    ),
    "kaplan_meier": TestSpec(
        key="kaplan_meier",
        label="Kaplan-Meier survival",
        question_type="time_to_event",
        requires={"time": "time", "event": "event_indicator"},
        n_groups=None,
        paired=False,
        nonparametric=True,
        rationale="Estimating survival curves for one or more groups without covariate adjustment.",
    ),
    "cox_ph": TestSpec(
        key="cox_ph",
        label="Cox proportional hazards regression",
        question_type="time_to_event",
        requires={"time": "time", "event": "event_indicator"},
        n_groups=None,
        paired=False,
        nonparametric=False,
        rationale="Time-to-event analysis adjusted for covariates, assuming proportional hazards.",
    ),
    "icc": TestSpec(
        key="icc",
        label="Intraclass correlation coefficient",
        question_type="agreement",
        requires={"rater_a": "numeric", "rater_b": "numeric"},
        n_groups=None,
        paired=True,
        nonparametric=False,
        rationale="Measuring agreement between two raters on a numeric scale.",
    ),
    "cohen_kappa": TestSpec(
        key="cohen_kappa",
        label="Cohen's kappa",
        question_type="agreement",
        requires={"rater_a": "nominal", "rater_b": "nominal"},
        n_groups=None,
        paired=True,
        nonparametric=True,
        rationale="Measuring agreement between two raters on a categorical scale.",
    ),
}


def _outcome_type(var_types: dict[str, Any]) -> str | None:
    return var_types.get("outcome") if isinstance(var_types.get("outcome"), str) else None


def _predictors(var_types: dict[str, Any]) -> list[str]:
    p = var_types.get("predictors")
    if isinstance(p, list):
        return [str(x) for x in p]
    if isinstance(p, str):
        return [p]
    return []


def recommend(
    *,
    question_type: str,
    var_types: dict[str, Any],
    n_groups: int | None = None,
    paired: bool = False,
    normality_ok: bool | None = None,
    equal_var_ok: bool | None = None,
    min_expected_count: float | None = None,
    intent: str | None = None,
    covariates: bool | None = None,
) -> tuple[str, str]:
    if question_type == "group_comparison":
        return _recommend_group_comparison(
            var_types=var_types,
            n_groups=n_groups,
            paired=paired,
            normality_ok=normality_ok,
            min_expected_count=min_expected_count,
        )
    if question_type == "association":
        return _recommend_association(
            var_types=var_types,
            normality_ok=normality_ok,
            intent=intent,
        )
    if question_type == "time_to_event":
        return _recommend_time_to_event(var_types=var_types, covariates=covariates)
    if question_type == "agreement":
        return _recommend_agreement(var_types=var_types)
    raise ValueError(f"unknown question_type: {question_type}")


def _spec(key: str) -> TestSpec:
    return CATALOGUE[key]


def _recommend_group_comparison(
    *,
    var_types: dict[str, Any],
    n_groups: int | None,
    paired: bool,
    normality_ok: bool | None,
    min_expected_count: float | None,
) -> tuple[str, str]:
    outcome = _outcome_type(var_types)
    if outcome == "nominal":
        if min_expected_count is not None and min_expected_count < 5:
            return "fisher_exact", _spec("fisher_exact").rationale
        return "chi_squared", _spec("chi_squared").rationale

    if outcome in ("numeric", "ordinal"):
        if n_groups is None or n_groups == 2:
            if paired:
                return (
                    ("paired_t", _spec("paired_t").rationale)
                    if normality_ok is not False
                    else ("wilcoxon_signed", _spec("wilcoxon_signed").rationale)
                )
            return (
                ("independent_t", _spec("independent_t").rationale)
                if normality_ok is not False
                else ("mann_whitney", _spec("mann_whitney").rationale)
            )
        # n_groups >= 3
        if paired:
            return "rm_anova", _spec("rm_anova").rationale
        return (
            ("one_way_anova", _spec("one_way_anova").rationale)
            if normality_ok is not False
            else ("kruskal_wallis", _spec("kruskal_wallis").rationale)
        )
    if outcome == "event_indicator":
        if min_expected_count is not None and min_expected_count < 5:
            return "fisher_exact", _spec("fisher_exact").rationale
        return "chi_squared", _spec("chi_squared").rationale
    raise ValueError(f"cannot recommend group_comparison with outcome={outcome!r}")


def _recommend_association(
    *,
    var_types: dict[str, Any],
    normality_ok: bool | None,
    intent: str | None,
) -> tuple[str, str]:
    outcome = _outcome_type(var_types)
    predictors = _predictors(var_types)

    if outcome == "event_indicator" or outcome == "binary":
        return "logistic", _spec("logistic").rationale

    if intent == "predict":
        if len(predictors) >= 2:
            return "multiple_linear", _spec("multiple_linear").rationale
        return "linear_regression", _spec("linear_regression").rationale

    x = var_types.get("x")
    y = var_types.get("y")
    if x == "numeric" and y == "numeric":
        return (
            ("pearson", _spec("pearson").rationale)
            if normality_ok is not False
            else ("spearman", _spec("spearman").rationale)
        )
    if outcome == "numeric" and len(predictors) >= 2:
        return "multiple_linear", _spec("multiple_linear").rationale
    if outcome == "numeric" and len(predictors) == 1:
        return "linear_regression", _spec("linear_regression").rationale
    return (
        ("pearson", _spec("pearson").rationale)
        if normality_ok is not False
        else ("spearman", _spec("spearman").rationale)
    )


def _recommend_time_to_event(
    *,
    var_types: dict[str, Any],
    covariates: bool | None,
) -> tuple[str, str]:
    has_covariates = bool(covariates) or bool(var_types.get("covariates"))
    if has_covariates:
        return "cox_ph", _spec("cox_ph").rationale
    return "kaplan_meier", _spec("kaplan_meier").rationale


def _recommend_agreement(*, var_types: dict[str, Any]) -> tuple[str, str]:
    a = var_types.get("rater_a")
    b = var_types.get("rater_b")
    if a == "numeric" and b == "numeric":
        return "icc", _spec("icc").rationale
    return "cohen_kappa", _spec("cohen_kappa").rationale
