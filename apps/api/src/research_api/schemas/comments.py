"""Phase 11 — manuscript comment Pydantic schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# Six manuscript sections + the synthetic "FrontMatter" target so comments
# can anchor to authors / affiliations / ethics text.
CommentSection = Literal[
    "Abstract",
    "Introduction",
    "Methodology",
    "Results",
    "Discussion",
    "Conclusion",
    "FrontMatter",
]


class CommentCreate(BaseModel):
    section_name: CommentSection
    anchor_start: int = Field(ge=0)
    anchor_end: int = Field(ge=0)
    body: str = Field(min_length=1, max_length=5000)


class CommentUpdate(BaseModel):
    body: str | None = Field(default=None, min_length=1, max_length=5000)
    resolved: bool | None = None


class CommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    section_name: str
    anchor_start: int
    anchor_end: int
    body: str
    resolved: bool
    created_at: datetime
    updated_at: datetime
