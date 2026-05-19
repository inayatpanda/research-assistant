"""Phase 14 (MP14) — PROSPERO draft repository."""
from __future__ import annotations

from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import ProsperoDraft, new_id


class ProsperoRepository(Protocol):
    async def get(
        self, review_id: str, user_id: str
    ) -> ProsperoDraft | None: ...
    async def create(
        self,
        *,
        project_id: str,
        review_id: str,
        fields: dict[str, Any],
        user_id: str,
    ) -> ProsperoDraft: ...
    async def update_fields(
        self,
        *,
        review_id: str,
        merge: dict[str, Any],
        user_id: str,
    ) -> ProsperoDraft | None: ...


class SqliteProsperoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(
        self, review_id: str, user_id: str
    ) -> ProsperoDraft | None:
        stmt = select(ProsperoDraft).where(
            ProsperoDraft.review_id == review_id,
            ProsperoDraft.user_id == user_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def create(
        self,
        *,
        project_id: str,
        review_id: str,
        fields: dict[str, Any],
        user_id: str,
    ) -> ProsperoDraft:
        row = ProsperoDraft(
            id=new_id(),
            user_id=user_id,
            project_id=project_id,
            review_id=review_id,
            fields=fields,
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def update_fields(
        self,
        *,
        review_id: str,
        merge: dict[str, Any],
        user_id: str,
    ) -> ProsperoDraft | None:
        row = await self.get(review_id, user_id)
        if row is None:
            return None
        new_fields = dict(row.fields or {})
        new_fields.update(merge)
        # Reassign to make sure SQLAlchemy detects the mutation on the JSON
        # column (in-place mutation of a JSON dict can be missed).
        row.fields = new_fields
        await self.session.commit()
        await self.session.refresh(row)
        return row
