from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ArticleNoteUpsert(BaseModel):
    # Generous cap for free-form research notes. Empty allowed (clears the note).
    content: str = Field(default="", max_length=100_000)


class ArticleNoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str | None  # None when no row exists yet
    user_id: str
    article_id: str
    content: str
    updated_at: datetime | None
