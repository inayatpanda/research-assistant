"""Phase 17 (MP17) — AnalysisPopulation Pydantic schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PopulationDefinition(BaseModel):
    """``definition`` payload — a pandas ``query()`` expression + label."""

    filter: str = Field(default="", description="pandas query() expression")
    label: str = Field(default="", description="human-readable label")


class PopulationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    definition: PopulationDefinition = Field(default_factory=PopulationDefinition)
    study_assignment_field: str = Field(min_length=1, max_length=255)
    treatment_received_field: str | None = Field(default=None, max_length=255)


class PopulationUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    definition: PopulationDefinition | None = None
    study_assignment_field: str | None = Field(default=None, max_length=255)
    treatment_received_field: str | None = Field(default=None, max_length=255)


class PopulationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    dataset_id: str
    name: str
    definition: dict[str, Any]
    study_assignment_field: str
    treatment_received_field: str | None
    created_at: datetime


class PopulationApplyPreview(BaseModel):
    """Preview the row count + first few rows after applying ``filter``."""

    n_before: int
    n_after: int
    head_rows: list[dict[str, Any]]
