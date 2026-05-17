from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ArticleNoteUpsert(BaseModel):
    content: str  # empty allowed


class ArticleNoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str | None  # None when no row exists yet
    user_id: str
    article_id: str
    content: str
    updated_at: datetime | None
