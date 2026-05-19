from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

HighlightColour = Literal["intro", "method", "results", "discussion"]
SectionName = Literal["Introduction", "Methodology", "Results", "Discussion"]


class BoundingRect(BaseModel):
    x0: float = Field(ge=0, le=1)
    y0: float = Field(ge=0, le=1)
    x1: float = Field(ge=0, le=1)
    y1: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def _reject_inverted(self) -> "BoundingRect":
        if self.x1 < self.x0:
            raise ValueError("x1 must be >= x0")
        if self.y1 < self.y0:
            raise ValueError("y1 must be >= y0")
        return self


class BoundingCoords(BaseModel):
    # Cap rect count so a malicious client cannot push a huge JSON into the column.
    rects: list[BoundingRect] = Field(min_length=1, max_length=64)


class HighlightCreate(BaseModel):
    page_number: int = Field(ge=1)
    selected_text: str = Field(min_length=1, max_length=10_000)
    colour: HighlightColour
    section: SectionName
    bounding_coords: BoundingCoords
    user_note: str | None = Field(default=None, max_length=4_000)
    sort_order: int = 0


class HighlightUpdate(BaseModel):
    # Reject unknown keys so a stale frontend / typo never silently no-ops.
    # FastAPI maps Pydantic ValidationError → HTTP 422.
    model_config = ConfigDict(extra="forbid")

    user_note: str | None = Field(default=None, max_length=4_000)
    ai_summary: str | None = Field(default=None, max_length=2_000)
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
