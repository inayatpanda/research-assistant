from __future__ import annotations

from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import ArticleNote, new_id


class ArticleNoteRepository(Protocol):
    async def get(self, article_id: str, user_id: str) -> ArticleNote | None: ...
    async def upsert(
        self, *, article_id: str, content: str, user_id: str
    ) -> ArticleNote: ...


class SqliteArticleNoteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, article_id: str, user_id: str) -> ArticleNote | None:
        stmt = select(ArticleNote).where(
            ArticleNote.article_id == article_id, ArticleNote.user_id == user_id
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def upsert(
        self, *, article_id: str, content: str, user_id: str
    ) -> ArticleNote:
        existing = await self.get(article_id, user_id)
        if existing is not None:
            existing.content = content
            await self.session.commit()
            await self.session.refresh(existing)
            return existing
        new_note = ArticleNote(
            id=new_id(), user_id=user_id, article_id=article_id, content=content
        )
        self.session.add(new_note)
        await self.session.commit()
        await self.session.refresh(new_note)
        return new_note
