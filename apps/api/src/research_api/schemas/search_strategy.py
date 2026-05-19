"""Pydantic schemas for search strategies (Phase 19)."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SearchDatabase = Literal[
    "PubMed", "Embase", "Cochrane", "Web of Science", "Scopus", "Other"
]
TranslationTarget = Literal["embase", "cochrane", "wos"]


class SearchStrategyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    database: SearchDatabase
    query_text: str = Field(min_length=1, max_length=20_000)
    mesh_term_ids: list[str] = Field(default_factory=list)
    translated_from_id: str | None = None
    is_locked: bool = False


class SearchStrategyUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    database: SearchDatabase | None = None
    query_text: str | None = Field(default=None, max_length=20_000)
    mesh_term_ids: list[str] | None = None
    is_locked: bool | None = None


class SearchStrategyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    review_id: str
    name: str
    database: str
    query_text: str
    mesh_term_ids: list[str]
    translated_from_id: str | None
    is_locked: bool
    warnings: list[str] | None
    created_at: datetime
    updated_at: datetime


class TranslateResponse(BaseModel):
    translated_query: str
    warnings: list[str] = Field(default_factory=list)
    target: TranslationTarget
