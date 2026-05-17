from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ManuscriptSectionName = Literal[
    "Introduction",
    "Methodology",
    "Results",
    "Discussion",
    "Abstract",
    "Conclusion",
]


class ManuscriptSectionUpsert(BaseModel):
    section_name: ManuscriptSectionName
    content: str = Field(default="", max_length=200_000)


class ManuscriptSectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str | None  # None when synthesized (no row yet)
    user_id: str
    project_id: str
    section_name: ManuscriptSectionName
    content: str
    word_count: int
    updated_at: datetime | None
