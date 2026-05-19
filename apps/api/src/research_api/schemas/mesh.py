"""Pydantic schemas for MeSH terms (Phase 19)."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MeshSource = Literal["user_added", "ncbi_lookup"]


class MeshTermCreate(BaseModel):
    descriptor_ui: str = Field(min_length=1, max_length=32)
    descriptor_name: str = Field(min_length=1, max_length=500)
    scope_note: str | None = None
    tree_numbers: list[str] = Field(default_factory=list)
    entry_terms: list[str] = Field(default_factory=list)
    source: MeshSource = "user_added"


class MeshTermRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    descriptor_ui: str
    descriptor_name: str
    scope_note: str | None
    tree_numbers: list[str]
    entry_terms: list[str]
    source: str
    created_at: datetime


class MeshSearchHit(BaseModel):
    """A single MeSH descriptor as parsed from NCBI E-utilities."""

    descriptor_ui: str
    descriptor_name: str
    scope_note: str | None = None
    tree_numbers: list[str] = Field(default_factory=list)
    entry_terms: list[str] = Field(default_factory=list)


class MeshSearchResponse(BaseModel):
    query: str
    hits: list[MeshSearchHit]


class MeshSuggestRequest(BaseModel):
    """Optional override of PICO if the FE wants to suggest without persisting."""

    population: str | None = None
    intervention: str | None = None
    comparator: str | None = None
    outcome: str | None = None
