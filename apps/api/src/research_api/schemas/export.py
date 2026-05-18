"""Pydantic schemas for the export/import endpoints."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from ..services.citation_format import CitationStyle

ExportFormat = Literal["docx", "pdf", "bundle"]


class BibliographyEntryRead(BaseModel):
    """One ordered, formatted reference list entry."""

    number: int
    article_id: str
    formatted_entry: str
    first_section: str


class BibliographyResponse(BaseModel):
    style: CitationStyle
    entries: list[BibliographyEntryRead]


class BundleExportRequest(BaseModel):
    """Bundle export is fully driven by the URL path's project_id; the body
    carries no additional knobs (yet)."""

    model_config = ConfigDict(extra="forbid")


class BundleImportResponse(BaseModel):
    """Returned after a successful JSON-bundle import."""

    project_id: str
    counts: dict[str, int]
