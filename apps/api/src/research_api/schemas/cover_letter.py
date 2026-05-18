"""Phase 12 — Cover-letter Pydantic schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

# JournalKey alias — the value is a key from the JournalTemplate catalogue
# (services/journal_templates/catalogue.py::JOURNALS). Kept as a plain str at
# this layer; the route validates against the live catalogue.
JournalKey = str


class CoverLetterRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    target_journal: JournalKey | None
    novelty_points: list[str]
    body_html: str
    ai_model: str | None
    created_at: datetime
    updated_at: datetime


class CoverLetterUpdate(BaseModel):
    """PATCH payload — any subset of these may be sent."""

    target_journal: JournalKey | None = None
    novelty_points: list[str] | None = Field(default=None, max_length=12)
    body_html: str | None = Field(default=None, max_length=20000)

    @field_validator("novelty_points")
    @classmethod
    def _strip_blank(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        cleaned = [s.strip() for s in v if isinstance(s, str) and s.strip()]
        # Keep at most 12 bullets after cleaning to limit AI prompt size.
        return cleaned[:12]


class CoverLetterDraftRequest(BaseModel):
    """POST /draft body — overrides are optional; the route falls back to
    whatever is currently persisted on the cover_letters row."""

    target_journal: JournalKey | None = None
    novelty_points: list[str] | None = Field(default=None, max_length=12)
