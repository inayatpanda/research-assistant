"""Phase 15 (MP15) — Living systematic review schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

LivingSchedule = Literal["daily", "weekly", "monthly"]
LivingHitDecision = Literal["new", "dismissed", "accepted"]


class LivingReviewJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    review_id: str
    pubmed_query: str
    schedule: LivingSchedule
    enabled: bool
    last_run_at: datetime | None
    last_hit_count: int | None
    created_at: datetime
    updated_at: datetime


class LivingReviewJobUpsert(BaseModel):
    """Body for POST upsert — the job is keyed by (project_id, review)."""

    pubmed_query: str = Field(..., min_length=1, max_length=4000)
    schedule: LivingSchedule = "weekly"
    enabled: bool = True


class LivingReviewJobPatch(BaseModel):
    pubmed_query: str | None = Field(default=None, min_length=1, max_length=4000)
    schedule: LivingSchedule | None = None
    enabled: bool | None = None


class LivingReviewHitRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    job_id: str
    run_at: datetime
    pmid: str
    title: str
    decision: LivingHitDecision
    seen_in_baseline: bool
    created_at: datetime


class LivingReviewHitDecisionPatch(BaseModel):
    decision: Literal["dismissed", "accepted"]


class LivingReviewRunResult(BaseModel):
    """Returned by ``POST .../run-now`` so the UI can show what landed."""

    job_id: str
    new_hits: int
    total_fetched: int
    ran_at: datetime
