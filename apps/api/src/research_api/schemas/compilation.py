from __future__ import annotations

from pydantic import BaseModel

from .highlight import HighlightColour, SectionName


class CompiledCard(BaseModel):
    """One card in the compilation view. The frontend renders these as
    (source highlight · user paraphrase · citation) rows."""

    highlight_id: str
    article_id: str
    citation: str  # server-formatted inline citation (e.g. 'Doe et al., 2024')
    article_title: str
    article_authors: list[str]
    article_year: int | None
    article_journal: str | None
    article_doi: str | None
    page_number: int
    selected_text: str
    user_note: str | None
    ai_summary: str | None
    section: SectionName
    colour: HighlightColour
    sort_order: int


class CompilationView(BaseModel):
    project_id: str
    colour: HighlightColour
    section: SectionName
    cards: list[CompiledCard]


class CardDraftResponse(BaseModel):
    highlight_id: str
    draft: str  # CITE tokens already replaced server-side
    used_citation: str  # the inline citation actually used


class SectionDraftResponse(BaseModel):
    project_id: str
    colour: HighlightColour
    section: SectionName
    draft: str
    used_citations: list[str]


class ReorderItem(BaseModel):
    highlight_id: str
    sort_order: int


class ReorderRequest(BaseModel):
    items: list[ReorderItem]
