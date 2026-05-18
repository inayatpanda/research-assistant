"""Phase 12 — Cover-letter repository.

One row per (project_id, user_id) per the UNIQUE constraint. The route
layer calls `get_or_create` so the first GET on a fresh project auto-mints
an empty row instead of 404-ing.
"""
from __future__ import annotations

from typing import Protocol

from sqlalchemy import delete as sa_delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import CoverLetter, new_id


_UNSET = object()


class CoverLetterRepository(Protocol):
    async def get_or_create(
        self, *, project_id: str, user_id: str
    ) -> CoverLetter: ...
    async def get(
        self, *, project_id: str, user_id: str
    ) -> CoverLetter | None: ...
    async def update(
        self,
        *,
        project_id: str,
        user_id: str,
        target_journal: str | None | object = _UNSET,
        novelty_points: list[str] | None | object = _UNSET,
        body_html: str | None | object = _UNSET,
        ai_model: str | None | object = _UNSET,
    ) -> CoverLetter | None: ...
    async def delete(
        self, *, project_id: str, user_id: str
    ) -> CoverLetter | None: ...


class SqliteCoverLetterRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(
        self, *, project_id: str, user_id: str
    ) -> CoverLetter | None:
        stmt = select(CoverLetter).where(
            CoverLetter.project_id == project_id,
            CoverLetter.user_id == user_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_or_create(
        self, *, project_id: str, user_id: str
    ) -> CoverLetter:
        existing = await self.get(project_id=project_id, user_id=user_id)
        if existing is not None:
            return existing
        row = CoverLetter(
            id=new_id(),
            user_id=user_id,
            project_id=project_id,
            target_journal=None,
            novelty_points=[],
            body_html="",
            ai_model=None,
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def update(
        self,
        *,
        project_id: str,
        user_id: str,
        target_journal: str | None | object = _UNSET,
        novelty_points: list[str] | None | object = _UNSET,
        body_html: str | None | object = _UNSET,
        ai_model: str | None | object = _UNSET,
    ) -> CoverLetter | None:
        row = await self.get(project_id=project_id, user_id=user_id)
        if row is None:
            return None
        if target_journal is not _UNSET:
            row.target_journal = target_journal  # type: ignore[assignment]
        if novelty_points is not _UNSET:
            # Treat None as "set to empty" for predictability — callers that
            # want to leave the field alone simply omit the kwarg.
            row.novelty_points = list(novelty_points or [])  # type: ignore[arg-type]
        if body_html is not _UNSET:
            row.body_html = body_html or ""  # type: ignore[assignment]
        if ai_model is not _UNSET:
            row.ai_model = ai_model  # type: ignore[assignment]
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def delete(
        self, *, project_id: str, user_id: str
    ) -> CoverLetter | None:
        existing = await self.get(project_id=project_id, user_id=user_id)
        if existing is None:
            return None
        await self.session.execute(
            sa_delete(CoverLetter).where(
                CoverLetter.project_id == project_id,
                CoverLetter.user_id == user_id,
            )
        )
        await self.session.commit()
        return existing
