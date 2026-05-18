"""Phase 11 — Manuscript margin-comment repository.

All methods are scoped by user_id. Listing optionally filters by
`section_name` and `resolved`.
"""
from __future__ import annotations

from typing import Protocol

from sqlalchemy import delete as sa_delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import ManuscriptComment, new_id


# Sentinel for "leave unchanged" on optional patch fields.
_UNSET = object()


class CommentRepository(Protocol):
    async def list_for_section(
        self,
        *,
        project_id: str,
        user_id: str,
        section_name: str | None = None,
        resolved: bool | None = None,
    ) -> list[ManuscriptComment]: ...
    async def get(
        self, comment_id: str, user_id: str
    ) -> ManuscriptComment | None: ...
    async def create(
        self,
        *,
        project_id: str,
        user_id: str,
        section_name: str,
        anchor_start: int,
        anchor_end: int,
        body: str,
    ) -> ManuscriptComment: ...
    async def update(
        self,
        comment_id: str,
        user_id: str,
        *,
        body: str | None = None,
        resolved: bool | None = None,
    ) -> ManuscriptComment | None: ...
    async def delete(
        self, comment_id: str, user_id: str
    ) -> ManuscriptComment | None: ...


class SqliteCommentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_section(
        self,
        *,
        project_id: str,
        user_id: str,
        section_name: str | None = None,
        resolved: bool | None = None,
    ) -> list[ManuscriptComment]:
        stmt = select(ManuscriptComment).where(
            ManuscriptComment.project_id == project_id,
            ManuscriptComment.user_id == user_id,
        )
        if section_name is not None:
            stmt = stmt.where(ManuscriptComment.section_name == section_name)
        if resolved is not None:
            stmt = stmt.where(ManuscriptComment.resolved == resolved)
        stmt = stmt.order_by(ManuscriptComment.created_at.asc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def get(
        self, comment_id: str, user_id: str
    ) -> ManuscriptComment | None:
        stmt = select(ManuscriptComment).where(
            ManuscriptComment.id == comment_id,
            ManuscriptComment.user_id == user_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def create(
        self,
        *,
        project_id: str,
        user_id: str,
        section_name: str,
        anchor_start: int,
        anchor_end: int,
        body: str,
    ) -> ManuscriptComment:
        row = ManuscriptComment(
            id=new_id(),
            user_id=user_id,
            project_id=project_id,
            section_name=section_name,
            anchor_start=anchor_start,
            anchor_end=anchor_end,
            body=body,
            resolved=False,
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def update(
        self,
        comment_id: str,
        user_id: str,
        *,
        body: str | None = None,
        resolved: bool | None = None,
    ) -> ManuscriptComment | None:
        existing = await self.get(comment_id, user_id)
        if existing is None:
            return None
        if body is not None:
            existing.body = body
        if resolved is not None:
            existing.resolved = resolved
        await self.session.commit()
        await self.session.refresh(existing)
        return existing

    async def delete(
        self, comment_id: str, user_id: str
    ) -> ManuscriptComment | None:
        existing = await self.get(comment_id, user_id)
        if existing is None:
            return None
        await self.session.execute(
            sa_delete(ManuscriptComment).where(
                ManuscriptComment.id == comment_id,
                ManuscriptComment.user_id == user_id,
            )
        )
        await self.session.commit()
        return existing
