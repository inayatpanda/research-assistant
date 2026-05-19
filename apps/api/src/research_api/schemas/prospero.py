"""Phase 14 (MP14) — PROSPERO registration draft Pydantic schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProsperoDraftRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    review_id: str
    fields: dict[str, Any]
    updated_at: datetime


class ProsperoDraftPatch(BaseModel):
    """Partial-merge body — any of the 22 fields, or arbitrary string blobs."""

    fields: dict[str, str] = Field(default_factory=dict)
