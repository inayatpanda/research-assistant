"""Phase 12 — Reviewer-response Pydantic schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CommentResponse(BaseModel):
    """Single segmented comment + the author's drafted reply."""

    comment_text: str = Field(min_length=1, max_length=10000)
    response_html: str = Field(default="", max_length=20000)


class ReviewerResponseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    reviewer_label: str
    comments: list[CommentResponse]
    created_at: datetime
    updated_at: datetime


class ReviewerResponseCreate(BaseModel):
    """POST body — `raw_comments` is the user-pasted block of reviewer text.

    The route calls the AI to segment + draft initial responses; the
    resulting `comments` list is persisted on a new row.
    """

    reviewer_label: str = Field(min_length=1, max_length=64)
    raw_comments: str = Field(min_length=1, max_length=50000)


class ReviewerResponseUpdate(BaseModel):
    """PATCH body — both fields optional; `comments` is a full overwrite."""

    reviewer_label: str | None = Field(default=None, min_length=1, max_length=64)
    comments: list[CommentResponse] | None = None

    @field_validator("comments")
    @classmethod
    def _trim_blank_text(
        cls, v: list[CommentResponse] | None
    ) -> list[CommentResponse] | None:
        if v is None:
            return None
        # Drop rows whose comment_text is whitespace-only.
        out: list[CommentResponse] = []
        for row in v:
            if row.comment_text.strip():
                out.append(row)
        return out
