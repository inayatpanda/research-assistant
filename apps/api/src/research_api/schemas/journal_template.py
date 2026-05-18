"""Phase 8.7 — Pydantic schema for the journal-template catalogue."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


ReferenceStyle = Literal["vancouver", "apa", "harvard"]


class JournalTemplate(BaseModel):
    key: str = Field(min_length=1, max_length=64)
    label: str
    max_total_words: int
    max_words_by_section: dict[str, int]
    required_sections: list[str]
    structured_abstract: bool
    reference_style: ReferenceStyle
    max_figures: int | None = None
    max_tables: int | None = None
