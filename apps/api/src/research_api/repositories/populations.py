"""Phase 17 (MP17) — AnalysisPopulation repository."""
from __future__ import annotations

from typing import Any

from sqlalchemy import delete as sa_delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import AnalysisPopulation, new_id


class SqliteAnalysisPopulationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_dataset(
        self, dataset_id: str, user_id: str
    ) -> list[AnalysisPopulation]:
        stmt = (
            select(AnalysisPopulation)
            .where(
                AnalysisPopulation.dataset_id == dataset_id,
                AnalysisPopulation.user_id == user_id,
            )
            .order_by(AnalysisPopulation.created_at.asc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get(
        self, population_id: str, user_id: str
    ) -> AnalysisPopulation | None:
        stmt = select(AnalysisPopulation).where(
            AnalysisPopulation.id == population_id,
            AnalysisPopulation.user_id == user_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def create(
        self,
        *,
        dataset_id: str,
        name: str,
        definition: dict[str, Any],
        study_assignment_field: str,
        treatment_received_field: str | None,
        user_id: str,
    ) -> AnalysisPopulation:
        row = AnalysisPopulation(
            id=new_id(),
            user_id=user_id,
            dataset_id=dataset_id,
            name=name,
            definition=definition,
            study_assignment_field=study_assignment_field,
            treatment_received_field=treatment_received_field,
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def update(
        self,
        *,
        population_id: str,
        user_id: str,
        name: str | None,
        definition: dict[str, Any] | None,
        study_assignment_field: str | None,
        treatment_received_field: str | None,
    ) -> AnalysisPopulation | None:
        row = await self.get(population_id, user_id)
        if row is None:
            return None
        if name is not None:
            row.name = name
        if definition is not None:
            row.definition = definition
        if study_assignment_field is not None:
            row.study_assignment_field = study_assignment_field
        if treatment_received_field is not None:
            row.treatment_received_field = treatment_received_field
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def delete(self, population_id: str, user_id: str) -> bool:
        row = await self.get(population_id, user_id)
        if row is None:
            return False
        await self.session.execute(
            sa_delete(AnalysisPopulation).where(
                AnalysisPopulation.id == population_id,
                AnalysisPopulation.user_id == user_id,
            )
        )
        await self.session.commit()
        return True
