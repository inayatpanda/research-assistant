from __future__ import annotations

from typing import Any, Protocol

from sqlalchemy import delete as sa_delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Analysis, AnalysisResult, Dataset, new_id


class AnalysisRepository(Protocol):
    async def create(
        self,
        *,
        project_id: str,
        dataset_id: str,
        question_type: str,
        chosen_test: str,
        recommendation_rationale: str,
        variables: dict[str, Any],
        status: str,
        user_id: str,
    ) -> Analysis: ...
    async def get(self, analysis_id: str, user_id: str) -> Analysis | None: ...
    async def get_with_dataset(
        self, analysis_id: str, user_id: str
    ) -> tuple[Analysis, Dataset] | None: ...
    async def get_result(
        self, analysis_id: str, user_id: str
    ) -> AnalysisResult | None: ...
    async def list_for_dataset(
        self, *, project_id: str, dataset_id: str, user_id: str
    ) -> list[Analysis]: ...
    async def list_for_project(
        self, project_id: str, user_id: str
    ) -> list[Analysis]: ...
    async def update_status(
        self, analysis_id: str, status: str, user_id: str
    ) -> Analysis | None: ...
    async def update_result(
        self,
        *,
        analysis_id: str,
        summary: dict[str, Any],
        assumptions: dict[str, Any],
        chart: dict[str, Any] | None,
        user_id: str,
    ) -> AnalysisResult | None: ...
    async def update_interpretation(
        self, *, analysis_id: str, ai_interpretation: str, user_id: str
    ) -> AnalysisResult | None: ...
    async def delete(self, analysis_id: str, user_id: str) -> None: ...


class SqliteAnalysisRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        project_id: str,
        dataset_id: str,
        question_type: str,
        chosen_test: str,
        recommendation_rationale: str,
        variables: dict[str, Any],
        status: str,
        user_id: str,
    ) -> Analysis:
        row = Analysis(
            id=new_id(),
            user_id=user_id,
            project_id=project_id,
            dataset_id=dataset_id,
            question_type=question_type,
            chosen_test=chosen_test,
            recommendation_rationale=recommendation_rationale,
            variables=variables,
            status=status,
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def get(self, analysis_id: str, user_id: str) -> Analysis | None:
        stmt = select(Analysis).where(
            Analysis.id == analysis_id, Analysis.user_id == user_id
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_with_dataset(
        self, analysis_id: str, user_id: str
    ) -> tuple[Analysis, Dataset] | None:
        a = await self.get(analysis_id, user_id)
        if a is None:
            return None
        stmt = select(Dataset).where(
            Dataset.id == a.dataset_id, Dataset.user_id == user_id
        )
        ds = (await self.session.execute(stmt)).scalar_one_or_none()
        if ds is None:
            return None
        return a, ds

    async def get_result(
        self, analysis_id: str, user_id: str
    ) -> AnalysisResult | None:
        stmt = select(AnalysisResult).where(
            AnalysisResult.analysis_id == analysis_id,
            AnalysisResult.user_id == user_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_for_dataset(
        self, *, project_id: str, dataset_id: str, user_id: str
    ) -> list[Analysis]:
        stmt = (
            select(Analysis)
            .where(
                Analysis.project_id == project_id,
                Analysis.dataset_id == dataset_id,
                Analysis.user_id == user_id,
            )
            .order_by(Analysis.created_at.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_for_project(
        self, project_id: str, user_id: str
    ) -> list[Analysis]:
        stmt = (
            select(Analysis)
            .where(
                Analysis.project_id == project_id,
                Analysis.user_id == user_id,
            )
            .order_by(Analysis.created_at.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def update_status(
        self, analysis_id: str, status: str, user_id: str
    ) -> Analysis | None:
        existing = await self.get(analysis_id, user_id)
        if existing is None:
            return None
        existing.status = status
        await self.session.commit()
        await self.session.refresh(existing)
        return existing

    async def update_result(
        self,
        *,
        analysis_id: str,
        summary: dict[str, Any],
        assumptions: dict[str, Any],
        chart: dict[str, Any] | None,
        user_id: str,
    ) -> AnalysisResult | None:
        # Verify the analysis exists for this user before writing a result row.
        analysis = await self.get(analysis_id, user_id)
        if analysis is None:
            return None
        existing = await self.get_result(analysis_id, user_id)
        if existing is not None:
            existing.summary = summary
            existing.assumptions = assumptions
            existing.chart = chart
            await self.session.commit()
            await self.session.refresh(existing)
            return existing
        row = AnalysisResult(
            id=new_id(),
            user_id=user_id,
            analysis_id=analysis_id,
            summary=summary,
            assumptions=assumptions,
            chart=chart,
            ai_interpretation=None,
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def update_interpretation(
        self, *, analysis_id: str, ai_interpretation: str, user_id: str
    ) -> AnalysisResult | None:
        existing = await self.get_result(analysis_id, user_id)
        if existing is None:
            return None
        existing.ai_interpretation = ai_interpretation
        await self.session.commit()
        await self.session.refresh(existing)
        return existing

    async def delete(self, analysis_id: str, user_id: str) -> None:
        # Manually cascade in case SQLite FK PRAGMA is off.
        await self.session.execute(
            sa_delete(AnalysisResult).where(
                AnalysisResult.analysis_id == analysis_id,
                AnalysisResult.user_id == user_id,
            )
        )
        await self.session.execute(
            sa_delete(Analysis).where(
                Analysis.id == analysis_id, Analysis.user_id == user_id
            )
        )
        await self.session.commit()
