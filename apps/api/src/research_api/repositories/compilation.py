"""Compilation read model — highlights JOIN articles, grouped by colour, sorted."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Article, Highlight
from ..schemas.highlight import HighlightColour


@dataclass(frozen=True)
class CompiledCardRow:
    """A flat row joining one highlight with its parent article. Service layer
    converts this to the wire-level CompiledCard with a formatted citation."""

    highlight_id: str
    article_id: str
    article_title: str
    article_authors: list[str]
    article_year: int | None
    article_journal: str | None
    article_doi: str | None
    page_number: int
    selected_text: str
    user_note: str | None
    ai_summary: str | None
    section: str
    colour: str
    sort_order: int


class CompilationRepository(Protocol):
    async def list_cards(
        self, project_id: str, colour: HighlightColour, user_id: str
    ) -> list[CompiledCardRow]: ...


class SqliteCompilationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_cards(
        self, project_id: str, colour: HighlightColour, user_id: str
    ) -> list[CompiledCardRow]:
        stmt = (
            select(Highlight, Article)
            .join(Article, Article.id == Highlight.article_id)
            .where(
                Article.project_id == project_id,
                Article.user_id == user_id,
                Highlight.user_id == user_id,
                Highlight.colour == colour,
            )
            .order_by(
                Highlight.sort_order.asc(),
                Highlight.page_number.asc(),
                Highlight.created_at.asc(),
            )
        )
        rows = (await self.session.execute(stmt)).all()
        return [
            CompiledCardRow(
                highlight_id=h.id,
                article_id=a.id,
                article_title=a.title,
                article_authors=list(a.authors or []),
                article_year=a.year,
                article_journal=a.journal,
                article_doi=a.doi,
                page_number=h.page_number,
                selected_text=h.selected_text,
                user_note=h.user_note,
                ai_summary=h.ai_summary,
                section=h.section,
                colour=h.colour,
                sort_order=h.sort_order,
            )
            for (h, a) in rows
        ]
