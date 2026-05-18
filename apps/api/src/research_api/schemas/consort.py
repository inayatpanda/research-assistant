"""Phase 8.7 — Pydantic schemas for CONSORT 2010 flow data."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ConsortData(BaseModel):
    """Mutable payload — every counter is optional (NULL until first entered)."""

    enrollment_assessed: int | None = Field(default=None, ge=0)
    enrollment_excluded: int | None = Field(default=None, ge=0)
    enrollment_excluded_reasons: dict[str, int] | None = None
    randomised: int | None = Field(default=None, ge=0)
    allocated_intervention: int | None = Field(default=None, ge=0)
    allocated_control: int | None = Field(default=None, ge=0)
    intervention_received: int | None = Field(default=None, ge=0)
    control_received: int | None = Field(default=None, ge=0)
    intervention_lost_followup: int | None = Field(default=None, ge=0)
    control_lost_followup: int | None = Field(default=None, ge=0)
    intervention_discontinued: int | None = Field(default=None, ge=0)
    control_discontinued: int | None = Field(default=None, ge=0)
    intervention_analysed: int | None = Field(default=None, ge=0)
    control_analysed: int | None = Field(default=None, ge=0)


class ConsortRead(ConsortData):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    created_at: datetime
    updated_at: datetime


class ConsortGetResponse(BaseModel):
    """GET /consort response — data + computed flow + SVG (base64) + warnings."""

    data: ConsortRead
    warnings: list[str]
    svg_base64: str
