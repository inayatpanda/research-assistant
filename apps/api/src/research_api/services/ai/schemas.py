from __future__ import annotations

from pydantic import BaseModel, Field


class CitationMetadata(BaseModel):
    """Bibliographic metadata extracted from a research article."""

    title: str
    authors: list[str] = Field(default_factory=list)
    journal: str | None = None
    year: int | None = None
    volume: str | None = None
    issue: str | None = None
    pages: str | None = None
    doi: str | None = None
    confidence: float = 0.0  # 0.0-1.0
