"""Phase 13.5 (MP13.5) — DatasetPlot repository (CRUD)."""
from __future__ import annotations

from typing import Any, Protocol

from sqlalchemy import delete as sa_delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import DatasetPlot, new_id


class PlotRepository(Protocol):
    async def list_for_dataset(
        self, dataset_id: str, user_id: str
    ) -> list[DatasetPlot]: ...
    async def get(self, plot_id: str, user_id: str) -> DatasetPlot | None: ...
    async def create(
        self,
        *,
        project_id: str,
        dataset_id: str,
        title: str,
        spec: dict[str, Any],
        png_data_uri: str,
        user_id: str,
    ) -> DatasetPlot: ...
    async def update_png(
        self,
        *,
        plot_id: str,
        png_data_uri: str,
        user_id: str,
    ) -> DatasetPlot | None: ...
    async def delete(self, plot_id: str, user_id: str) -> bool: ...


class SqlitePlotRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_dataset(
        self, dataset_id: str, user_id: str
    ) -> list[DatasetPlot]:
        stmt = (
            select(DatasetPlot)
            .where(
                DatasetPlot.dataset_id == dataset_id,
                DatasetPlot.user_id == user_id,
            )
            .order_by(DatasetPlot.created_at.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get(self, plot_id: str, user_id: str) -> DatasetPlot | None:
        stmt = select(DatasetPlot).where(
            DatasetPlot.id == plot_id, DatasetPlot.user_id == user_id
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def create(
        self,
        *,
        project_id: str,
        dataset_id: str,
        title: str,
        spec: dict[str, Any],
        png_data_uri: str,
        user_id: str,
    ) -> DatasetPlot:
        row = DatasetPlot(
            id=new_id(),
            user_id=user_id,
            project_id=project_id,
            dataset_id=dataset_id,
            title=title,
            spec=spec,
            png_data_uri=png_data_uri,
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def update_png(
        self,
        *,
        plot_id: str,
        png_data_uri: str,
        user_id: str,
    ) -> DatasetPlot | None:
        row = await self.get(plot_id, user_id)
        if row is None:
            return None
        row.png_data_uri = png_data_uri
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def delete(self, plot_id: str, user_id: str) -> bool:
        row = await self.get(plot_id, user_id)
        if row is None:
            return False
        await self.session.execute(
            sa_delete(DatasetPlot).where(
                DatasetPlot.id == plot_id, DatasetPlot.user_id == user_id
            )
        )
        await self.session.commit()
        return True
