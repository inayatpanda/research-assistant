from __future__ import annotations

from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import ManuscriptSection, new_id


def _word_count(text: str) -> int:
    return len((text or "").split())


class ManuscriptSectionRepository(Protocol):
    async def get(
        self, *, project_id: str, section_name: str, user_id: str
    ) -> ManuscriptSection | None: ...
    async def upsert(
        self, *, project_id: str, section_name: str, content: str, user_id: str
    ) -> ManuscriptSection: ...


class SqliteManuscriptSectionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(
        self, *, project_id: str, section_name: str, user_id: str
    ) -> ManuscriptSection | None:
        stmt = select(ManuscriptSection).where(
            ManuscriptSection.project_id == project_id,
            ManuscriptSection.section_name == section_name,
            ManuscriptSection.user_id == user_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def upsert(
        self, *, project_id: str, section_name: str, content: str, user_id: str
    ) -> ManuscriptSection:
        existing = await self.get(
            project_id=project_id, section_name=section_name, user_id=user_id
        )
        if existing is not None:
            existing.content = content
            existing.word_count = _word_count(content)
            await self.session.commit()
            await self.session.refresh(existing)
            return existing
        row = ManuscriptSection(
            id=new_id(),
            user_id=user_id,
            project_id=project_id,
            section_name=section_name,
            content=content,
            word_count=_word_count(content),
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row
