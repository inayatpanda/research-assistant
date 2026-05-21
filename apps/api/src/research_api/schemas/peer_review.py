"""Phase 4.6 — Pydantic schemas for AI peer reviews."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


PeerReviewSourceType = Literal["manuscript", "uploaded_pdf", "uploaded_docx"]
PeerReviewRecommendation = Literal[
    "reject", "major_revision", "minor_revision", "accept"
]
PeerReviewStatus = Literal["pending", "completed", "failed"]


class PeerReviewCritique(BaseModel):
    """Structured AI critique. Lists may be empty but every key is present."""

    overall_impression: str = Field(default="")
    strengths: list[str] = Field(default_factory=list)
    major_issues: list[str] = Field(default_factory=list)
    minor_issues: list[str] = Field(default_factory=list)
    methodological_concerns: list[str] = Field(default_factory=list)
    statistical_concerns: list[str] = Field(default_factory=list)
    reporting_concerns: list[str] = Field(default_factory=list)
    presentation_concerns: list[str] = Field(default_factory=list)
    references_concerns: list[str] = Field(default_factory=list)
    recommendation: PeerReviewRecommendation = "major_revision"
    suggestions_for_improvement: list[str] = Field(default_factory=list)


class PeerReviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    source_type: PeerReviewSourceType
    source_title: str
    source_file_ref: dict[str, Any] | None = None
    manuscript_snapshot: dict[str, Any] | None = None
    critique: dict[str, Any]
    recommendation: PeerReviewRecommendation
    ai_model: str
    status: PeerReviewStatus
    error: str | None = None
    created_at: datetime
    updated_at: datetime


class PeerReviewSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    source_type: PeerReviewSourceType
    source_title: str
    recommendation: PeerReviewRecommendation
    ai_model: str
    status: PeerReviewStatus
    created_at: datetime
    updated_at: datetime


class PeerReviewManuscriptRequest(BaseModel):
    """Trigger an AI peer review of the project's current manuscript."""

    # Optional override (e.g. user wants to label the review). Defaults to
    # the manuscript title.
    title_override: str | None = None
