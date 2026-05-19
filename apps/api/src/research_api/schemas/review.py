from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

ReviewStage = Literal["title_abstract", "full_text"]
ScreeningDecision = Literal["pending", "include", "exclude", "maybe"]
ExclusionCategory = Literal[
    "population", "intervention", "outcome",
    "study_design", "language", "duplicate", "other",
]
RoBTool = Literal[
    "rob2",
    "robins_i",
    "nos",
    "amstar2",
    # Phase 19 (MP19) — 7 JBI critical appraisal tools.
    "jbi_case_series",
    "jbi_case_report",
    "jbi_cohort",
    "jbi_cross_sectional",
    "jbi_quasi_experimental",
    "jbi_diagnostic_accuracy",
    "jbi_prevalence",
]
RoBJudgement = Literal["low", "some_concerns", "high", "critical", "unclear"]
DatabaseName = Literal[
    "PubMed", "Embase", "Cochrane", "Scopus",
    "Web of Science", "Google Scholar", "Other",
]


class ReviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    pico_population: str | None
    pico_intervention: str | None
    pico_comparator: str | None
    pico_outcome: str | None
    eligibility_inclusion: str | None
    eligibility_exclusion: str | None
    # Phase 19 (MP19) — Mixed-design RoB.
    tool_per_study: bool = False
    created_at: datetime
    updated_at: datetime


class ReviewUpdate(BaseModel):
    pico_population: str | None = None
    pico_intervention: str | None = None
    pico_comparator: str | None = None
    pico_outcome: str | None = None
    eligibility_inclusion: str | None = None
    eligibility_exclusion: str | None = None
    tool_per_study: bool | None = None


class SearchRecordCreate(BaseModel):
    database_name: DatabaseName
    query_string: str = Field(min_length=1, max_length=10_000)
    date_searched: datetime
    n_results: int = Field(ge=0)
    notes: str | None = None


class SearchRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    review_id: str
    database_name: str
    query_string: str
    date_searched: datetime
    n_results: int
    notes: str | None
    created_at: datetime


class SearchRecordUpdate(BaseModel):
    database_name: DatabaseName | None = None
    query_string: str | None = Field(default=None, max_length=10_000)
    date_searched: datetime | None = None
    n_results: int | None = Field(default=None, ge=0)
    notes: str | None = None


class ScreeningRecordCreate(BaseModel):
    article_id: str
    stage: ReviewStage
    decision: ScreeningDecision = "pending"
    exclusion_category: ExclusionCategory | None = None
    reason: str | None = None


class ScreeningRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    review_id: str
    article_id: str
    stage: str
    decision: str
    exclusion_category: str | None
    reason: str | None
    reviewer_id: str | None
    ai_suggestion: dict[str, Any] | None
    decided_at: datetime | None
    created_at: datetime


class ScreeningRecordUpdate(BaseModel):
    decision: ScreeningDecision | None = None
    exclusion_category: ExclusionCategory | None = None
    reason: str | None = None


class AIScreeningSuggestRequest(BaseModel):
    pass


class AIScreeningSuggestResponse(BaseModel):
    vote: ScreeningDecision
    reason: str
    model: str


class RoBAssessmentCreate(BaseModel):
    article_id: str
    tool: RoBTool
    domain_answers: dict[str, str]
    notes: str | None = None


class RoBAssessmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    review_id: str
    article_id: str
    tool: str
    domain_answers: dict[str, str]
    overall_auto: str
    overall_override: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class RoBAssessmentUpdate(BaseModel):
    domain_answers: dict[str, str] | None = None
    overall_override: RoBJudgement | None = None
    notes: str | None = None


class ExtractionRecordCreate(BaseModel):
    article_id: str
    fields: dict[str, Any]


class ExtractionRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    review_id: str
    article_id: str
    fields: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ExtractionRecordUpdate(BaseModel):
    fields: dict[str, Any]


class PrismaCounts(BaseModel):
    identified: int
    after_dedupe: int
    screened: int
    excluded_title: int
    full_text_assessed: int
    excluded_full: dict[str, int]
    included: int


class PrismaPushRequest(BaseModel):
    pass


class RoBPushRequest(BaseModel):
    pass


class ExtractionPushRequest(BaseModel):
    pass


class SearchPushRequest(BaseModel):
    pass
