"""Pydantic schemas for SR depth (narrative synthesis + outcome instruments).

Phase 19 (MP19).
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Direction = Literal["higher_better", "lower_better", "neutral"]

StudyDesign = Literal[
    "rct",
    "cohort",
    "case_control",
    "case_series",
    "case_report",
    "cross_sectional",
    "quasi_experimental",
    "systematic_review",
    "diagnostic_accuracy",
    "prevalence",
    "qualitative",
    "other",
]


class StudyValueEntry(BaseModel):
    article_id: str
    group_label: str = Field(min_length=1, max_length=120)
    value: float | None = None
    sd_or_ci: str | None = None  # free-text, e.g. "1.2" or "0.9–1.5"
    n: int | None = Field(default=None, ge=0)


class OutcomeInstrumentCreate(BaseModel):
    outcome_label: str = Field(min_length=1, max_length=255)
    instrument_name: str = Field(min_length=1, max_length=255)
    score_range_low: float | None = None
    score_range_high: float | None = None
    mid: float | None = None
    study_values: list[StudyValueEntry] = Field(default_factory=list)


class OutcomeInstrumentUpdate(BaseModel):
    outcome_label: str | None = Field(default=None, max_length=255)
    instrument_name: str | None = Field(default=None, max_length=255)
    score_range_low: float | None = None
    score_range_high: float | None = None
    mid: float | None = None
    study_values: list[StudyValueEntry] | None = None


class OutcomeInstrumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    review_id: str
    outcome_label: str
    instrument_name: str
    score_range_low: float | None
    score_range_high: float | None
    mid: float | None
    study_values: list[dict]
    created_at: datetime


class NarrativeSynthesisCreate(BaseModel):
    outcome_label: str = Field(min_length=1, max_length=255)
    instrument: str = Field(min_length=1, max_length=255)
    range_text: str | None = Field(default=None, max_length=255)
    direction: Direction = "neutral"
    narrative_html: str = ""
    study_citations: list[str] = Field(default_factory=list)


class NarrativeSynthesisUpdate(BaseModel):
    outcome_label: str | None = Field(default=None, max_length=255)
    instrument: str | None = Field(default=None, max_length=255)
    range_text: str | None = Field(default=None, max_length=255)
    direction: Direction | None = None
    narrative_html: str | None = None
    study_citations: list[str] | None = None


class NarrativeSynthesisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    review_id: str
    outcome_label: str
    instrument: str
    range_text: str | None
    direction: str
    narrative_html: str
    study_citations: list[str]
    created_at: datetime
    updated_at: datetime
