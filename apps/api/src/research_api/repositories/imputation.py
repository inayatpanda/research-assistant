"""Phase 17 (MP17) — ImputationRun repository."""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import ImputationRun, new_id


class SqliteImputationRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_dataset(
        self, dataset_id: str, user_id: str
    ) -> list[ImputationRun]:
        stmt = (
            select(ImputationRun)
            .where(
                ImputationRun.dataset_id == dataset_id,
                ImputationRun.user_id == user_id,
            )
            .order_by(ImputationRun.created_at.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get(self, run_id: str, user_id: str) -> ImputationRun | None:
        stmt = select(ImputationRun).where(
            ImputationRun.id == run_id, ImputationRun.user_id == user_id
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def create(
        self,
        *,
        dataset_id: str,
        method: str,
        n_imputations: int,
        seed: int,
        target_cols: list[str],
        pooled_summary: dict[str, Any],
        user_id: str,
    ) -> ImputationRun:
        row = ImputationRun(
            id=new_id(),
            user_id=user_id,
            dataset_id=dataset_id,
            method=method,
            n_imputations=n_imputations,
            seed=seed,
            target_cols=target_cols,
            pooled_summary=pooled_summary,
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row
