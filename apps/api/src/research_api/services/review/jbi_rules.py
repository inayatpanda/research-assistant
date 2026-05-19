"""Joanna Briggs Institute (JBI) critical appraisal catalogue.

Phase 19 (MP19). Mirrors ``rob_rules.py`` so the existing RoB endpoints
can serve JBI tools without a fork. Seven tools (Case Series, Case
Reports, Cohort, Cross-sectional, Quasi-experimental, Diagnostic Test
Accuracy, Prevalence). Each item answered with Yes / No / Unclear /
NA. Overall = low/moderate/high/unclear via percentage of Yes.

Threshold (mirrors JBI manual recommendations):
- low risk    >= 70% Yes
- moderate    50-69% Yes
- high        < 50% Yes
- unclear     when every answer is "unclear" / "na"
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .rob_rules import Domain, Tool

_JBI_ANSWERS = ("yes", "no", "unclear", "na")
_JBI_SEVERITY: dict[str, int] = {"yes": 0, "na": 0, "unclear": 1, "no": 2}


def _items(prompts: tuple[tuple[str, str], ...]) -> tuple[Domain, ...]:
    return tuple(
        Domain(key=k, label=k, question=q, answers=_JBI_ANSWERS) for k, q in prompts
    )


# ─── Tool item catalogues ──────────────────────────────────────────────


_CASE_SERIES = (
    ("cs_1", "Were there clear criteria for inclusion in the case series?"),
    ("cs_2", "Was the condition measured in a standard, reliable way for all participants?"),
    ("cs_3", "Were valid methods used for identification of the condition?"),
    ("cs_4", "Did the case series have consecutive inclusion of participants?"),
    ("cs_5", "Did the case series have complete inclusion of participants?"),
    ("cs_6", "Was there clear reporting of the demographics of the participants?"),
    ("cs_7", "Was there clear reporting of clinical information of the participants?"),
    ("cs_8", "Were the outcomes or follow-up results of cases clearly reported?"),
    ("cs_9", "Was there clear reporting of the presenting site(s)/clinic(s) demographic information?"),
    ("cs_10", "Was statistical analysis appropriate?"),
)


_CASE_REPORT = (
    ("cr_1", "Were patient's demographic characteristics clearly described?"),
    ("cr_2", "Was the patient's history clearly described and presented as a timeline?"),
    ("cr_3", "Was the current clinical condition of the patient on presentation clearly described?"),
    ("cr_4", "Were diagnostic tests or assessment methods and the results clearly described?"),
    ("cr_5", "Was the intervention(s) or treatment procedure(s) clearly described?"),
    ("cr_6", "Was the post-intervention clinical condition clearly described?"),
    ("cr_7", "Were adverse events (harms) or unanticipated events identified and described?"),
    ("cr_8", "Does the case report provide takeaway lessons?"),
)


_COHORT = (
    ("co_1", "Were the two groups similar and recruited from the same population?"),
    ("co_2", "Were the exposures measured similarly to assign people to both exposed and unexposed groups?"),
    ("co_3", "Was the exposure measured in a valid and reliable way?"),
    ("co_4", "Were confounding factors identified?"),
    ("co_5", "Were strategies to deal with confounding factors stated?"),
    ("co_6", "Were the groups/participants free of the outcome at the start of the study?"),
    ("co_7", "Were the outcomes measured in a valid and reliable way?"),
    ("co_8", "Was the follow-up time reported and sufficient to be long enough for outcomes to occur?"),
    ("co_9", "Was follow-up complete, and if not, were the reasons described and explored?"),
    ("co_10", "Were strategies to address incomplete follow-up utilised?"),
    ("co_11", "Was appropriate statistical analysis used?"),
)


_CROSS_SECTIONAL = (
    ("xs_1", "Were the criteria for inclusion in the sample clearly defined?"),
    ("xs_2", "Were the study subjects and the setting described in detail?"),
    ("xs_3", "Was the exposure measured in a valid and reliable way?"),
    ("xs_4", "Were objective, standard criteria used for measurement of the condition?"),
    ("xs_5", "Were confounding factors identified?"),
    ("xs_6", "Were strategies to deal with confounding factors stated?"),
    ("xs_7", "Were the outcomes measured in a valid and reliable way?"),
    ("xs_8", "Was appropriate statistical analysis used?"),
)


_QUASI_EXPERIMENTAL = (
    ("qe_1", "Is it clear in the study what is the 'cause' and what is the 'effect'?"),
    ("qe_2", "Were the participants included in any comparisons similar?"),
    ("qe_3", "Were participants included in any comparisons receiving similar treatment/care, other than the exposure or intervention of interest?"),
    ("qe_4", "Was there a control group?"),
    ("qe_5", "Were there multiple measurements of the outcome both pre and post the intervention/exposure?"),
    ("qe_6", "Was follow-up complete and, if not, were differences between groups in terms of their follow-up adequately described and analyzed?"),
    ("qe_7", "Were the outcomes of participants included in any comparisons measured in the same way?"),
    ("qe_8", "Were outcomes measured in a reliable way?"),
    ("qe_9", "Was appropriate statistical analysis used?"),
)


_DIAGNOSTIC_TEST_ACCURACY = (
    ("dta_1", "Was a consecutive or random sample of patients enrolled?"),
    ("dta_2", "Was a case-control design avoided?"),
    ("dta_3", "Did the study avoid inappropriate exclusions?"),
    ("dta_4", "Were the index test results interpreted without knowledge of the results of the reference standard?"),
    ("dta_5", "If a threshold was used, was it pre-specified?"),
    ("dta_6", "Is the reference standard likely to correctly classify the target condition?"),
    ("dta_7", "Were the reference standard results interpreted without knowledge of the results of the index test?"),
    ("dta_8", "Was there an appropriate interval between index test and reference standard?"),
    ("dta_9", "Did all patients receive a reference standard?"),
    ("dta_10", "Were all patients included in the analysis?"),
)


_PREVALENCE = (
    ("pv_1", "Was the sample frame appropriate to address the target population?"),
    ("pv_2", "Were study participants sampled in an appropriate way?"),
    ("pv_3", "Was the sample size adequate?"),
    ("pv_4", "Were the study subjects and the setting described in detail?"),
    ("pv_5", "Was the data analysis conducted with sufficient coverage of the identified sample?"),
    ("pv_6", "Were valid methods used for the identification of the condition?"),
    ("pv_7", "Was the condition measured in a standard, reliable way for all participants?"),
    ("pv_8", "Was there appropriate statistical analysis?"),
    ("pv_9", "Was the response rate adequate, and if not, was the low response rate managed appropriately?"),
)


def _tool(key: str, label: str, applies_to: tuple[str, ...], prompts: tuple[tuple[str, str], ...]) -> Tool:
    return Tool(
        key=key,
        label=label,
        applies_to=applies_to,
        domains=_items(prompts),
        answer_severity=dict(_JBI_SEVERITY),
    )


JBI_CASE_SERIES = _tool(
    "jbi_case_series",
    "JBI Critical Appraisal Tool — Case Series (10 items)",
    ("case_series",),
    _CASE_SERIES,
)
JBI_CASE_REPORT = _tool(
    "jbi_case_report",
    "JBI Critical Appraisal Tool — Case Reports (8 items)",
    ("case_report",),
    _CASE_REPORT,
)
JBI_COHORT = _tool(
    "jbi_cohort",
    "JBI Critical Appraisal Tool — Cohort Studies (11 items)",
    ("cohort",),
    _COHORT,
)
JBI_CROSS_SECTIONAL = _tool(
    "jbi_cross_sectional",
    "JBI Critical Appraisal Tool — Cross-sectional Studies (8 items)",
    ("cross_sectional",),
    _CROSS_SECTIONAL,
)
JBI_QUASI_EXPERIMENTAL = _tool(
    "jbi_quasi_experimental",
    "JBI Critical Appraisal Tool — Quasi-experimental Studies (9 items)",
    ("quasi_experimental",),
    _QUASI_EXPERIMENTAL,
)
JBI_DIAGNOSTIC = _tool(
    "jbi_diagnostic_accuracy",
    "JBI Critical Appraisal Tool — Diagnostic Test Accuracy Studies (10 items)",
    ("diagnostic_accuracy",),
    _DIAGNOSTIC_TEST_ACCURACY,
)
JBI_PREVALENCE = _tool(
    "jbi_prevalence",
    "JBI Critical Appraisal Tool — Prevalence Studies (9 items)",
    ("prevalence",),
    _PREVALENCE,
)


JBI_CATALOGUE: dict[str, Tool] = {
    JBI_CASE_SERIES.key: JBI_CASE_SERIES,
    JBI_CASE_REPORT.key: JBI_CASE_REPORT,
    JBI_COHORT.key: JBI_COHORT,
    JBI_CROSS_SECTIONAL.key: JBI_CROSS_SECTIONAL,
    JBI_QUASI_EXPERIMENTAL.key: JBI_QUASI_EXPERIMENTAL,
    JBI_DIAGNOSTIC.key: JBI_DIAGNOSTIC,
    JBI_PREVALENCE.key: JBI_PREVALENCE,
}


def derive_overall_jbi(tool_key: str, answers: dict[str, str]) -> str:
    """Compute the overall JBI risk-of-bias band from per-item answers.

    Returns one of ``"low" | "moderate" | "high" | "unclear"``.

    Raises:
        ValueError: when the tool is unknown or the answers dict carries
            answers outside the allowed set.
    """
    if tool_key not in JBI_CATALOGUE:
        raise ValueError(f"unknown JBI tool: {tool_key!r}")
    tool = JBI_CATALOGUE[tool_key]
    valid = {d.key for d in tool.domains}
    allowed_answers = set(_JBI_ANSWERS)
    for k, v in answers.items():
        if k not in valid:
            raise ValueError(f"unknown domain {k!r} for tool {tool_key!r}")
        if v not in allowed_answers:
            raise ValueError(f"invalid answer {v!r} for {tool_key}:{k}")

    rated = [v for v in answers.values() if v in {"yes", "no"}]
    if not rated:
        return "unclear"
    yes_count = sum(1 for v in rated if v == "yes")
    pct = 100.0 * yes_count / len(rated)
    if pct >= 70.0:
        return "low"
    if pct >= 50.0:
        return "moderate"
    return "high"


__all__ = [
    "JBI_CATALOGUE",
    "JBI_CASE_SERIES",
    "JBI_CASE_REPORT",
    "JBI_COHORT",
    "JBI_CROSS_SECTIONAL",
    "JBI_QUASI_EXPERIMENTAL",
    "JBI_DIAGNOSTIC",
    "JBI_PREVALENCE",
    "derive_overall_jbi",
]
