from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

QuestionType = Literal[
    "group_comparison",
    "association",
    "time_to_event",
    "agreement",
]

TestKey = Literal[
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
    # Phase 13 (MP13) — Extended catalogue.
    "mixed_effects_lm",
    "glm_poisson",
    "glm_binomial",
    "glm_gamma",
    "gee",
    "bootstrap_mean_diff",
    "permutation_test",
    "tost_equivalence",
    "tost_noninferiority",
    # Phase 17 (MP17) — Post-hoc pairwise comparisons.
    "post_hoc_tukey",
    "post_hoc_bonferroni",
    "post_hoc_dunns",
    "post_hoc_games_howell",
]

AnalysisStatus = Literal["draft", "ready", "running", "completed", "failed"]


class RecommendRequest(BaseModel):
    question_type: QuestionType
    variables: dict[str, str | list[str]]


class RecommendResponse(BaseModel):
    chosen_test: TestKey
    rationale: str
    assumption_warnings: list[str] = []


class AnalysisCreate(BaseModel):
    question_type: QuestionType
    chosen_test: TestKey
    variables: dict[str, Any]


class AnalysisResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    summary: dict[str, Any]
    assumptions: dict[str, Any]
    chart: dict[str, Any] | None
    ai_interpretation: str | None


class AnalysisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    dataset_id: str
    question_type: QuestionType
    chosen_test: TestKey
    recommendation_rationale: str
    variables: dict[str, Any]
    status: AnalysisStatus
    created_at: datetime
    # Phase 17 (MP17) — Population + lock.
    population_id: str | None = None
    is_locked: bool = False
    locked_at: datetime | None = None
    integrity_hash: str | None = None
    result: AnalysisResultRead | None = None


class InterpretRequest(BaseModel):
    pass


class InterpretResponse(BaseModel):
    ai_interpretation: str


class PushToManuscriptRequest(BaseModel):
    pass


class ChartLabelOverrides(BaseModel):
    """DEMO-FIX-C — Per-chart label overrides stored on AnalysisResult.chart.

    Every field is optional; an empty/missing value means "use the dataset
    display labels". When provided, these win over dataset display labels
    AND canonical column names.
    """

    x_label_override: str | None = None
    y_label_override: str | None = None
    title_override: str | None = None
    legend_label_overrides: dict[str, str] | None = None
