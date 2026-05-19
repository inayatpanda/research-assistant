"""Phase 13.5 (MP13.5) — AnalysisPlan + AnalysisPlanRun repository."""
from __future__ import annotations

from typing import Any, Protocol

from sqlalchemy import delete as sa_delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import AnalysisPlan, AnalysisPlanRun, new_id


class AnalysisPlanRepository(Protocol):
    async def list_for_project(
        self, project_id: str, user_id: str
    ) -> list[AnalysisPlan]: ...
    async def get(self, plan_id: str, user_id: str) -> AnalysisPlan | None: ...
    async def create(
        self,
        *,
        project_id: str,
        name: str,
        description: str | None,
        steps: list[dict[str, Any]],
        user_id: str,
    ) -> AnalysisPlan: ...
    async def update(
        self,
        *,
        plan_id: str,
        user_id: str,
        name: str | None,
        description: str | None,
        steps: list[dict[str, Any]] | None,
    ) -> AnalysisPlan | None: ...
    async def delete(self, plan_id: str, user_id: str) -> bool: ...
    async def list_runs(
        self, plan_id: str, user_id: str
    ) -> list[AnalysisPlanRun]: ...
    async def get_run(
        self, run_id: str, user_id: str
    ) -> AnalysisPlanRun | None: ...
    async def create_run(
        self,
        *,
        plan_id: str,
        dataset_id: str,
        result_blob: dict[str, Any],
        status: str,
        error: str | None,
        user_id: str,
    ) -> AnalysisPlanRun: ...


class SqliteAnalysisPlanRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_project(
        self, project_id: str, user_id: str
    ) -> list[AnalysisPlan]:
        stmt = (
            select(AnalysisPlan)
            .where(
                AnalysisPlan.project_id == project_id,
                AnalysisPlan.user_id == user_id,
            )
            .order_by(AnalysisPlan.created_at.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get(self, plan_id: str, user_id: str) -> AnalysisPlan | None:
        stmt = select(AnalysisPlan).where(
            AnalysisPlan.id == plan_id, AnalysisPlan.user_id == user_id
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def create(
        self,
        *,
        project_id: str,
        name: str,
        description: str | None,
        steps: list[dict[str, Any]],
        user_id: str,
    ) -> AnalysisPlan:
        row = AnalysisPlan(
            id=new_id(),
            user_id=user_id,
            project_id=project_id,
            name=name,
            description=description,
            steps=steps,
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def update(
        self,
        *,
        plan_id: str,
        user_id: str,
        name: str | None,
        description: str | None,
        steps: list[dict[str, Any]] | None,
    ) -> AnalysisPlan | None:
        row = await self.get(plan_id, user_id)
        if row is None:
            return None
        if name is not None:
            row.name = name
        if description is not None:
            row.description = description
        if steps is not None:
            row.steps = steps
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def delete(self, plan_id: str, user_id: str) -> bool:
        row = await self.get(plan_id, user_id)
        if row is None:
            return False
        await self.session.execute(
            sa_delete(AnalysisPlanRun).where(
                AnalysisPlanRun.plan_id == plan_id,
                AnalysisPlanRun.user_id == user_id,
            )
        )
        await self.session.execute(
            sa_delete(AnalysisPlan).where(
                AnalysisPlan.id == plan_id, AnalysisPlan.user_id == user_id
            )
        )
        await self.session.commit()
        return True

    async def list_runs(
        self, plan_id: str, user_id: str
    ) -> list[AnalysisPlanRun]:
        stmt = (
            select(AnalysisPlanRun)
            .where(
                AnalysisPlanRun.plan_id == plan_id,
                AnalysisPlanRun.user_id == user_id,
            )
            .order_by(AnalysisPlanRun.executed_at.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_run(
        self, run_id: str, user_id: str
    ) -> AnalysisPlanRun | None:
        stmt = select(AnalysisPlanRun).where(
            AnalysisPlanRun.id == run_id, AnalysisPlanRun.user_id == user_id
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def create_run(
        self,
        *,
        plan_id: str,
        dataset_id: str,
        result_blob: dict[str, Any],
        status: str,
        error: str | None,
        user_id: str,
    ) -> AnalysisPlanRun:
        row = AnalysisPlanRun(
            id=new_id(),
            user_id=user_id,
            plan_id=plan_id,
            dataset_id=dataset_id,
            result_blob=result_blob,
            status=status,
            error=error,
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row
