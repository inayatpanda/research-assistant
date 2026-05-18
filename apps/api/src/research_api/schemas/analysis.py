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
    result: AnalysisResultRead | None = None


class InterpretRequest(BaseModel):
    pass


class InterpretResponse(BaseModel):
    ai_interpretation: str


class PushToManuscriptRequest(BaseModel):
    pass
