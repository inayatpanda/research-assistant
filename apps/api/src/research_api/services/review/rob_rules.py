from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Domain:
    key: str
    label: str
    question: str
    answers: tuple[str, ...]
    critical: bool = False


@dataclass(frozen=True)
class Tool:
    key: str
    label: str
    applies_to: tuple[str, ...]
    domains: tuple[Domain, ...]
    answer_severity: dict[str, int] = field(default_factory=dict)


_ROB2_ANSWERS = ("low", "some_concerns", "high", "unclear")
_ROBINSI_ANSWERS = ("low", "moderate", "serious", "critical", "no_information")
_NOS_ANSWERS = ("yes", "no", "unclear")
_AMSTAR2_ANSWERS = ("yes", "partial_yes", "no")


ROB2 = Tool(
    key="rob2",
    label="RoB 2 (Cochrane Risk of Bias for randomised trials)",
    applies_to=("RCT", "randomised", "randomized_controlled_trial"),
    domains=(
        Domain("randomisation", "Randomisation process",
               "Was the allocation sequence random and adequately concealed?",
               _ROB2_ANSWERS),
        Domain("deviations", "Deviations from intended interventions",
               "Were deviations from the intended interventions balanced and analysed appropriately?",
               _ROB2_ANSWERS),
        Domain("missing_outcome", "Missing outcome data",
               "Was outcome data reasonably complete?",
               _ROB2_ANSWERS),
        Domain("measurement", "Measurement of the outcome",
               "Was the outcome measurement free from bias?",
               _ROB2_ANSWERS),
        Domain("reporting", "Selection of the reported result",
               "Was the reported result free from selective reporting?",
               _ROB2_ANSWERS),
    ),
    answer_severity={"low": 0, "unclear": 1, "some_concerns": 2, "high": 3},
)


ROBINS_I = Tool(
    key="robins_i",
    label="ROBINS-I (Risk of Bias in Non-randomised Studies of Interventions)",
    applies_to=("cohort", "case_control", "non_randomised", "observational"),
    domains=(
        Domain("confounding", "Bias due to confounding",
               "Was the analysis adequately controlled for confounding?",
               _ROBINSI_ANSWERS),
        Domain("selection", "Bias in selection of participants",
               "Were participants selected into the study without bias?",
               _ROBINSI_ANSWERS),
        Domain("classification", "Bias in classification of interventions",
               "Were the interventions clearly defined and classified?",
               _ROBINSI_ANSWERS),
        Domain("deviations", "Bias due to deviations from intended interventions",
               "Were deviations from intended interventions handled appropriately?",
               _ROBINSI_ANSWERS),
        Domain("missing_data", "Bias due to missing data",
               "Was missing outcome or covariate data addressed appropriately?",
               _ROBINSI_ANSWERS),
        Domain("measurement", "Bias in measurement of outcomes",
               "Were outcomes measured in a way that did not introduce bias?",
               _ROBINSI_ANSWERS),
        Domain("reporting", "Bias in selection of the reported result",
               "Was the reported result free from selective reporting?",
               _ROBINSI_ANSWERS),
    ),
    answer_severity={"low": 0, "moderate": 1, "no_information": 2, "serious": 3, "critical": 4},
)


_NOS_SELECTION = (
    Domain("sel_1", "Representativeness of exposed cohort",
           "Is the exposed cohort truly representative of the target population?",
           _NOS_ANSWERS),
    Domain("sel_2", "Selection of non-exposed",
           "Was the non-exposed cohort drawn from the same community?",
           _NOS_ANSWERS),
    Domain("sel_3", "Ascertainment of exposure",
           "Was exposure ascertained from a secure record or structured interview?",
           _NOS_ANSWERS),
    Domain("sel_4", "Outcome of interest not present at start",
           "Was it demonstrated the outcome was not present at the start of the study?",
           _NOS_ANSWERS),
)
_NOS_COMPARABILITY = (
    Domain("comp_1", "Comparability — primary factor",
           "Did the study control for the most important confounder?",
           _NOS_ANSWERS),
    Domain("comp_2", "Comparability — additional factor",
           "Did the study control for any additional confounders?",
           _NOS_ANSWERS),
)
_NOS_OUTCOME = (
    Domain("out_1", "Assessment of outcome",
           "Was outcome assessment independent and blinded, or by record linkage?",
           _NOS_ANSWERS),
    Domain("out_2", "Length of follow-up",
           "Was follow-up long enough for outcomes to occur?",
           _NOS_ANSWERS),
    Domain("out_3", "Adequacy of follow-up",
           "Was follow-up of cohorts complete or accounted for?",
           _NOS_ANSWERS),
)

NOS = Tool(
    key="nos",
    label="Newcastle-Ottawa Scale (cohort)",
    applies_to=("cohort", "case_control", "observational"),
    domains=(
        Domain("selection", "Selection",
               "Selection of study groups (4 stars maximum across sub-items).",
               _NOS_ANSWERS),
        Domain("comparability", "Comparability",
               "Comparability of cohorts on the basis of design or analysis (2 stars maximum).",
               _NOS_ANSWERS),
        Domain("outcome", "Outcome",
               "Ascertainment of outcome and adequacy of follow-up (3 stars maximum).",
               _NOS_ANSWERS),
    ),
    answer_severity={"yes": 0, "unclear": 1, "no": 2},
)


_NOS_SUBITEMS: dict[str, tuple[Domain, ...]] = {
    "selection": _NOS_SELECTION,
    "comparability": _NOS_COMPARABILITY,
    "outcome": _NOS_OUTCOME,
}


_AMSTAR2_ITEMS: tuple[tuple[str, str, bool], ...] = (
    ("a2_1", "Did the research questions and inclusion criteria include PICO?", False),
    ("a2_2", "Was the review conducted from a pre-established protocol?", True),
    ("a2_3", "Did the authors explain the selection of study designs?", False),
    ("a2_4", "Did the authors use a comprehensive literature search strategy?", True),
    ("a2_5", "Did the authors perform study selection in duplicate?", False),
    ("a2_6", "Did the authors perform data extraction in duplicate?", False),
    ("a2_7", "Did the authors provide a list of excluded studies and justify exclusions?", True),
    ("a2_8", "Did the authors describe the included studies in adequate detail?", False),
    ("a2_9", "Did the authors use a satisfactory technique for assessing risk of bias in individual studies?", True),
    ("a2_10", "Did the authors report on the sources of funding for the included studies?", False),
    ("a2_11", "Did the authors use appropriate methods for statistical combination of results?", True),
    ("a2_12", "Did the authors assess the potential impact of risk of bias on meta-analysis results?", False),
    ("a2_13", "Did the authors account for risk of bias when interpreting the results of the review?", True),
    ("a2_14", "Did the authors provide a satisfactory explanation for any heterogeneity observed?", False),
    ("a2_15", "Did the authors carry out an adequate investigation of publication bias and discuss its likely impact?", True),
    ("a2_16", "Did the authors report any potential sources of conflict of interest?", False),
)

AMSTAR2 = Tool(
    key="amstar2",
    label="AMSTAR-2 (assessment of systematic reviews)",
    applies_to=("systematic_review", "meta_analysis"),
    domains=tuple(
        Domain(key=k, label=k, question=q, answers=_AMSTAR2_ANSWERS, critical=c)
        for (k, q, c) in _AMSTAR2_ITEMS
    ),
    answer_severity={"yes": 0, "partial_yes": 1, "no": 2},
)


CATALOGUE: dict[str, Tool] = {
    "rob2": ROB2,
    "robins_i": ROBINS_I,
    "nos": NOS,
    "amstar2": AMSTAR2,
}


AMSTAR2_UNIFIED_MAPPING: dict[str, str] = {
    "high": "low",
    "moderate": "some_concerns",
    "low": "high",
    "critical_low": "critical",
}


def _validate_answers(tool: Tool, answers: dict[str, str]) -> None:
    valid = {d.key: set(d.answers) for d in tool.domains}
    for k, v in answers.items():
        if tool.key == "nos":
            allowed = {"yes", "no", "unclear"}
            if v not in allowed:
                raise ValueError(f"invalid answer {v!r} for {tool.key}:{k}")
            continue
        if tool.key == "amstar2":
            if v not in set(_AMSTAR2_ANSWERS):
                raise ValueError(f"invalid answer {v!r} for {tool.key}:{k}")
            continue
        if k not in valid:
            raise ValueError(f"unknown domain {k!r} for tool {tool.key!r}")
        if v not in valid[k]:
            raise ValueError(f"invalid answer {v!r} for {tool.key}:{k}")


def _rob2_overall(answers: dict[str, str]) -> str:
    has_high = False
    has_some = False
    has_unclear = False
    for v in answers.values():
        if v == "high":
            has_high = True
        elif v == "some_concerns":
            has_some = True
        elif v == "unclear":
            has_unclear = True
    if has_high:
        return "high"
    if has_some:
        return "some_concerns"
    if has_unclear:
        return "unclear"
    return "low"


_ROBINSI_RANK = {
    "low": 0,
    "moderate": 1,
    "no_information": 2,
    "serious": 3,
    "critical": 4,
}


def _robinsi_overall(answers: dict[str, str]) -> str:
    if not answers:
        return "low"
    worst = max(answers.values(), key=lambda v: _ROBINSI_RANK.get(v, -1))
    mapping = {
        "low": "low",
        "moderate": "some_concerns",
        "no_information": "unclear",
        "serious": "high",
        "critical": "critical",
    }
    return mapping[worst]


def _nos_overall(answers: dict[str, str]) -> str:
    stars = sum(1 for v in answers.values() if v == "yes")
    if stars >= 7:
        return "low"
    if stars >= 5:
        return "some_concerns"
    return "high"


def _amstar2_overall(answers: dict[str, str]) -> str:
    crit_weak = 0
    noncrit_weak = 0
    for d in AMSTAR2.domains:
        ans = answers.get(d.key, "no")
        is_weak = ans != "yes"
        if is_weak:
            if d.critical:
                crit_weak += 1
            else:
                noncrit_weak += 1
    if crit_weak >= 2:
        raw = "critical_low"
    elif crit_weak == 1:
        raw = "low"
    elif noncrit_weak > 1:
        raw = "moderate"
    else:
        raw = "high"
    return AMSTAR2_UNIFIED_MAPPING[raw]


def derive_overall(tool_key: str, domain_answers: dict[str, str]) -> str:
    if tool_key not in CATALOGUE:
        raise ValueError(f"unknown tool: {tool_key!r}")
    tool = CATALOGUE[tool_key]
    _validate_answers(tool, domain_answers)
    if tool_key == "rob2":
        return _rob2_overall(domain_answers)
    if tool_key == "robins_i":
        return _robinsi_overall(domain_answers)
    if tool_key == "nos":
        return _nos_overall(domain_answers)
    if tool_key == "amstar2":
        return _amstar2_overall(domain_answers)
    raise ValueError(f"unhandled tool: {tool_key!r}")


_DESIGN_TOOL_MAP: dict[str, str] = {
    "RCT": "rob2",
    "randomised": "rob2",
    "randomized_controlled_trial": "rob2",
    "cohort": "robins_i",
    "case_control": "robins_i",
    "non_randomised": "robins_i",
    "observational": "robins_i",
    "case_series": "robins_i",
    "cross_sectional": "robins_i",
    "systematic_review": "amstar2",
    "meta_analysis": "amstar2",
}


def select_tool_for_design(study_design: str) -> Tool | None:
    key = _DESIGN_TOOL_MAP.get(study_design)
    return CATALOGUE[key] if key else None
