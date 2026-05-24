from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .article import ArticleRead

ExtractionSource = Literal["ai", "crossref", "both", "none"]

# F1 — AI autofill from PDF upload.
# ``doi_match``     — Crossref resolved the DOI we scraped from the PDF.
# ``heuristic_only`` — we couldn't resolve a DOI, fell back to a regex guess.
# ``failed``         — neither path produced any usable fields.
AutofillStatus = Literal["doi_match", "heuristic_only", "failed"]

# Per-field provenance map (e.g. {"title": "doi", "year": "heuristic"}).
# Frontend uses this to render the "DOI autofilled" / "Heuristic guess" pill
# next to each field. Fields the user types by hand carry no entry (the
# absence of an entry implies ``"manual"``).
AutofillFieldSource = Literal["doi", "heuristic", "manual"]


class UploadResponse(BaseModel):
    article: ArticleRead
    duplicate_of: ArticleRead | None = None
    extraction_source: ExtractionSource = "none"
    extraction_error: str | None = None  # populated if AI failed; article still saved with minimal metadata

    # F1 — autofill outcome surfaced to the frontend so each row can render
    # a "DOI autofilled" / "Heuristic guess" pill next to the autofilled
    # fields. ``autofilled_by`` maps field-name → "doi"|"heuristic".
    autofill_status: AutofillStatus = "failed"
    autofilled_by: dict[str, AutofillFieldSource] = Field(default_factory=dict)
