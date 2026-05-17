from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from .article import ArticleRead

ExtractionSource = Literal["ai", "crossref", "both", "none"]


class UploadResponse(BaseModel):
    article: ArticleRead
    duplicate_of: ArticleRead | None = None
    extraction_source: ExtractionSource = "none"
    extraction_error: str | None = None  # populated if AI failed; article still saved with minimal metadata
