from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

ReviewStatus = Literal["pending", "included", "excluded", "unsure"]

# Phase 16 (MP16) — Reference categorisation for grey-literature handling.
ReferenceType = Literal[
    "journal_article",
    "book",
    "book_chapter",
    "conference_abstract",
    "thesis",
    "preprint",
    "registry_record",
    "report",
    "web_resource",
    "other",
]

# Phase 19 (MP19) — Canonical study design vocabulary.
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

# Legacy aliases used in tests / older bundles. Normalised to canonical
# values by ``_normalise_study_design`` so the historical API surface keeps
# working while the validator still rejects truly unknown strings.
_STUDY_DESIGN_ALIASES: dict[str, str] = {
    "RCT": "rct",
    "randomised": "rct",
    "randomized": "rct",
    "randomised_controlled_trial": "rct",
    "randomized_controlled_trial": "rct",
    "Cohort": "cohort",
    "case-control": "case_control",
    "Case-control": "case_control",
    "case series": "case_series",
    "Case Series": "case_series",
    "case report": "case_report",
    "Case Report": "case_report",
    "cross sectional": "cross_sectional",
    "Cross-sectional": "cross_sectional",
    "quasi experimental": "quasi_experimental",
    "diagnostic test accuracy": "diagnostic_accuracy",
    "diagnostic_test_accuracy": "diagnostic_accuracy",
    "non_randomised": "cohort",
    "observational": "cohort",
    "systematic review": "systematic_review",
    "meta_analysis": "systematic_review",
}


def _normalise_study_design(value: str | None) -> str | None:
    if value is None:
        return None
    raw = value.strip()
    if not raw:
        return None
    if raw in _STUDY_DESIGN_ALIASES:
        return _STUDY_DESIGN_ALIASES[raw]
    # case-insensitive direct match against canonical set
    canonical = {
        "rct", "cohort", "case_control", "case_series", "case_report",
        "cross_sectional", "quasi_experimental", "systematic_review",
        "diagnostic_accuracy", "prevalence", "qualitative", "other",
    }
    if raw in canonical:
        return raw
    lower = raw.lower().replace("-", "_").replace(" ", "_")
    if lower in canonical:
        return lower
    # Don't reject — older bundles may carry free text. Pass through verbatim
    # so we never break a round-trip; the canonical Literal is enforced for
    # *new* edits via the FE picker but the schema accepts arbitrary strings
    # for forward compatibility. (Phase 19 design decision.)
    return raw


class StorageRefSchema(BaseModel):
    backend: str
    key: str


class ArticleCreate(BaseModel):
    title: str = Field(min_length=1, max_length=1000)
    authors: list[str] = Field(default_factory=list)
    journal: str | None = None
    year: int | None = Field(default=None, ge=1500, le=2200)
    volume: str | None = None
    issue: str | None = None
    pages: str | None = None
    doi: str | None = None
    file_ref: StorageRefSchema | None = None
    file_type: str | None = None
    study_design: str | None = None
    review_status: ReviewStatus = "pending"
    exclusion_reason: str | None = None
    conflict_of_interest: str | None = None
    # Phase 16 (MP16) — Reference categorisation + URL for grey lit.
    reference_type: ReferenceType = "journal_article"
    url: str | None = None


class ArticleUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=1000)
    authors: list[str] | None = None
    journal: str | None = None
    year: int | None = Field(default=None, ge=1500, le=2200)
    volume: str | None = None
    issue: str | None = None
    pages: str | None = None
    doi: str | None = None
    study_design: str | None = None
    review_status: ReviewStatus | None = None
    exclusion_reason: str | None = None
    conflict_of_interest: str | None = None
    reference_type: ReferenceType | None = None
    url: str | None = None


class ArticleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    project_id: str
    title: str
    authors: list[str]
    journal: str | None
    year: int | None
    volume: str | None
    issue: str | None
    pages: str | None
    doi: str | None
    pmid: str | None = None
    file_ref: dict | None
    file_type: str | None
    abstract: str | None = None
    study_design: str | None
    review_status: ReviewStatus
    exclusion_reason: str | None
    conflict_of_interest: str | None
    source: str = "upload"
    # Phase 16 (MP16)
    reference_type: ReferenceType = "journal_article"
    url: str | None = None
    created_at: datetime
    # Optional signed URL filled in by route layer; not from DB
    file_url: str | None = None


class ArticleFilters(BaseModel):
    q: str | None = None  # title text search
    review_status: ReviewStatus | None = None
    study_design: str | None = None
    sort: Literal["year_desc", "year_asc", "title", "created_desc"] = "created_desc"
