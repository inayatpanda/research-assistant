from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ReviewStatus = Literal["pending", "included", "excluded", "unsure"]


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
    file_ref: dict | None
    file_type: str | None
    study_design: str | None
    review_status: ReviewStatus
    exclusion_reason: str | None
    conflict_of_interest: str | None
    created_at: datetime
    # Optional signed URL filled in by route layer; not from DB
    file_url: str | None = None


class ArticleFilters(BaseModel):
    q: str | None = None  # title text search
    review_status: ReviewStatus | None = None
    study_design: str | None = None
    sort: Literal["year_desc", "year_asc", "title", "created_desc"] = "created_desc"
