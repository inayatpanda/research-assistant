"""Phase 8.7 — SqliteConsortRepository: get-or-create + update by (project, user)."""
from __future__ import annotations

from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import ConsortData, new_id
from ..schemas.consort import ConsortData as ConsortPatch


class ConsortRepository(Protocol):
    async def get_or_create(self, *, project_id: str, user_id: str) -> ConsortData: ...
    async def update(
        self, *, project_id: str, user_id: str, patch: ConsortPatch
    ) -> ConsortData: ...


class SqliteConsortRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_or_create(self, *, project_id: str, user_id: str) -> ConsortData:
        stmt = select(ConsortData).where(
            ConsortData.project_id == project_id,
            ConsortData.user_id == user_id,
        )
        existing = (await self.session.execute(stmt)).scalar_one_or_none()
        if existing is not None:
            return existing
        row = ConsortData(id=new_id(), user_id=user_id, project_id=project_id)
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def update(
        self, *, project_id: str, user_id: str, patch: ConsortPatch
    ) -> ConsortData:
        row = await self.get_or_create(project_id=project_id, user_id=user_id)
        for k, v in patch.model_dump(exclude_unset=True).items():
            setattr(row, k, v)
        await self.session.commit()
        await self.session.refresh(row)
        return row
