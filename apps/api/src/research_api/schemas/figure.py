"""Phase 8.7 — Pydantic schemas for the figures resource."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


ImageMime = Literal["image/png", "image/jpeg", "image/svg+xml"]


class FigureRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    figure_number: int
    caption: str
    alt_text: str
    file_type: ImageMime
    width_px: int | None
    height_px: int | None
    byte_size: int
    file_url: str | None = None
    created_at: datetime
    updated_at: datetime


class FigureUpdate(BaseModel):
    caption: str | None = None
    alt_text: str | None = Field(default=None, max_length=500)


class FigureReorderRequest(BaseModel):
    ordered_figure_ids: list[str] = Field(min_length=1)
