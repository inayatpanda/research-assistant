from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

HighlightColour = Literal["intro", "method", "results", "discussion"]
SectionName = Literal["Introduction", "Methodology", "Results", "Discussion"]


class BoundingRect(BaseModel):
    x0: float = Field(ge=0, le=1)
    y0: float = Field(ge=0, le=1)
    x1: float = Field(ge=0, le=1)
    y1: float = Field(ge=0, le=1)


class BoundingCoords(BaseModel):
    rects: list[BoundingRect] = Field(min_length=1)


class HighlightCreate(BaseModel):
    page_number: int = Field(ge=1)
    selected_text: str = Field(min_length=1, max_length=10_000)
    colour: HighlightColour
    section: SectionName
    bounding_coords: BoundingCoords
    user_note: str | None = None
    sort_order: int = 0


class HighlightUpdate(BaseModel):
    user_note: str | None = None
    ai_summary: str | None = None
    sort_order: int | None = None


class HighlightRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    article_id: str
    page_number: int
    selected_text: str
    colour: HighlightColour
    section: SectionName
    bounding_coords: dict  # JSON shape; frontend parses with zod
    user_note: str | None
    ai_summary: str | None
    sort_order: int
    created_at: datetime
