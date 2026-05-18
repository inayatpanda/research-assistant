"""Phase 8.6 — Ingestion schemas.

Uniform `ArticleMetadata` shape returned by every ingest surface
(DOI / PubMed / RIS / BibTeX) BEFORE persistence.

`DuplicateGroup` describes a candidate group flagged for the user to review;
`MergeRequest` drives the merge endpoint.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .article import ArticleRead

ArticleSource = Literal["upload", "doi", "pubmed", "ris", "bibtex", "manual"]
DuplicateReason = Literal["doi_exact", "pmid_exact", "title_fuzzy"]


class ArticleMetadata(BaseModel):
    """Uniform shape returned by every ingest surface (DOI/PubMed/RIS/BibTeX)
    BEFORE the row is persisted. Maps 1:1 to ArticleCreate plus pmid /
    abstract / source."""

    title: str
    authors: list[str] = Field(default_factory=list)
    journal: str | None = None
    year: int | None = None
    volume: str | None = None
    issue: str | None = None
    pages: str | None = None
    doi: str | None = None
    pmid: str | None = None
    abstract: str | None = None
    source: ArticleSource


class ImportFromMetadataRequest(BaseModel):
    items: list[ArticleMetadata] = Field(min_length=1)


class DuplicateGroup(BaseModel):
    keep_candidate_id: str  # oldest row in the group (deterministic)
    candidate_ids: list[str] = Field(min_length=2)  # includes the keep candidate
    reason: DuplicateReason
    score: float = Field(ge=0.0, le=1.0)


class ImportFromMetadataResponse(BaseModel):
    created: list[ArticleRead]
    skipped_duplicates: list[ArticleRead]
    duplicate_groups: list[DuplicateGroup]


class MergeRequest(BaseModel):
    keep_id: str
    drop_ids: list[str] = Field(min_length=1)


class DoiLookupRequest(BaseModel):
    doi: str = Field(min_length=1)


class PubMedSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    retmax: int = Field(default=20, ge=1, le=100)


__all__ = [
    "ArticleSource",
    "DuplicateReason",
    "ArticleMetadata",
    "ImportFromMetadataRequest",
    "ImportFromMetadataResponse",
    "DuplicateGroup",
    "MergeRequest",
    "DoiLookupRequest",
    "PubMedSearchRequest",
]
