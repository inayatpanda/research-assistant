"""Phase 18 (MP18) — Repository for EconomicAnalysis + EconomicResult."""
from __future__ import annotations

from typing import Any

from sqlalchemy import delete as sa_delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Dataset, EconomicAnalysis, EconomicResult, new_id


class SqliteEconomicAnalysisRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_project(
        self, project_id: str, user_id: str
    ) -> list[EconomicAnalysis]:
        stmt = (
            select(EconomicAnalysis)
            .where(
                EconomicAnalysis.project_id == project_id,
                EconomicAnalysis.user_id == user_id,
            )
            .order_by(EconomicAnalysis.created_at.asc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get(
        self, analysis_id: str, user_id: str
    ) -> EconomicAnalysis | None:
        stmt = select(EconomicAnalysis).where(
            EconomicAnalysis.id == analysis_id,
            EconomicAnalysis.user_id == user_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_with_dataset(
        self, analysis_id: str, user_id: str
    ) -> tuple[EconomicAnalysis, Dataset | None] | None:
        analysis = await self.get(analysis_id, user_id)
        if analysis is None:
            return None
        if analysis.dataset_id is None:
            return analysis, None
        dstmt = select(Dataset).where(
            Dataset.id == analysis.dataset_id,
            Dataset.user_id == user_id,
        )
        dataset = (await self.session.execute(dstmt)).scalar_one_or_none()
        return analysis, dataset

    async def create(
        self,
        *,
        project_id: str,
        user_id: str,
        dataset_id: str | None,
        name: str,
        currency: str,
        time_horizon_months: int,
        perspective: str,
        discount_rate_costs: float,
        discount_rate_qalys: float,
        wtp_thresholds: list[int],
        utility_value_set: str,
        bootstrap_n: int,
        seed: int,
        treatment_col: str,
        comparator_label: str,
        intervention_label: str,
        cost_columns: list[dict[str, Any]],
    ) -> EconomicAnalysis:
        row = EconomicAnalysis(
            id=new_id(),
            user_id=user_id,
            project_id=project_id,
            dataset_id=dataset_id,
            name=name,
            currency=currency,
            time_horizon_months=time_horizon_months,
            perspective=perspective,
            discount_rate_costs=discount_rate_costs,
            discount_rate_qalys=discount_rate_qalys,
            wtp_thresholds=wtp_thresholds,
            utility_value_set=utility_value_set,
            bootstrap_n=bootstrap_n,
            seed=seed,
            treatment_col=treatment_col,
            comparator_label=comparator_label,
            intervention_label=intervention_label,
            cost_columns=cost_columns,
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def update(
        self,
        *,
        analysis_id: str,
        user_id: str,
        patch: dict[str, Any],
    ) -> EconomicAnalysis | None:
        row = await self.get(analysis_id, user_id)
        if row is None:
            return None
        for k, v in patch.items():
            if v is not None and hasattr(row, k):
                setattr(row, k, v)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def update_interpretation(
        self, *, analysis_id: str, user_id: str, ai_interpretation: str
    ) -> EconomicAnalysis | None:
        row = await self.get(analysis_id, user_id)
        if row is None:
            return None
        row.ai_interpretation = ai_interpretation
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def delete(self, analysis_id: str, user_id: str) -> bool:
        row = await self.get(analysis_id, user_id)
        if row is None:
            return False
        await self.session.execute(
            sa_delete(EconomicAnalysis).where(
                EconomicAnalysis.id == analysis_id,
                EconomicAnalysis.user_id == user_id,
            )
        )
        await self.session.commit()
        return True


class SqliteEconomicResultRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_for_analysis(
        self, analysis_id: str, user_id: str
    ) -> EconomicResult | None:
        stmt = select(EconomicResult).where(
            EconomicResult.economic_analysis_id == analysis_id,
            EconomicResult.user_id == user_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def upsert(
        self,
        *,
        analysis_id: str,
        user_id: str,
        mean_cost_diff: float,
        mean_qaly_diff: float,
        icer: float | None,
        dominance_status: str,
        nmb_at_thresholds: dict[str, Any],
        ceac_data: list[dict[str, Any]],
        plane_bootstrap: list[dict[str, Any]],
        sensitivity: dict[str, Any] | None,
        plane_png_uri: str,
        ceac_png_uri: str,
    ) -> EconomicResult:
        existing = await self.get_for_analysis(analysis_id, user_id)
        if existing is None:
            row = EconomicResult(
                id=new_id(),
                user_id=user_id,
                economic_analysis_id=analysis_id,
                mean_cost_diff=mean_cost_diff,
                mean_qaly_diff=mean_qaly_diff,
                icer=icer,
                dominance_status=dominance_status,
                nmb_at_thresholds=nmb_at_thresholds,
                ceac_data=ceac_data,
                plane_bootstrap=plane_bootstrap,
                sensitivity=sensitivity,
                plane_png_uri=plane_png_uri,
                ceac_png_uri=ceac_png_uri,
            )
            self.session.add(row)
        else:
            row = existing
            row.mean_cost_diff = mean_cost_diff
            row.mean_qaly_diff = mean_qaly_diff
            row.icer = icer
            row.dominance_status = dominance_status
            row.nmb_at_thresholds = nmb_at_thresholds
            row.ceac_data = ceac_data
            row.plane_bootstrap = plane_bootstrap
            row.sensitivity = sensitivity
            row.plane_png_uri = plane_png_uri
            row.ceac_png_uri = ceac_png_uri
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def update_sensitivity(
        self,
        *,
        analysis_id: str,
        user_id: str,
        sensitivity: dict[str, Any],
    ) -> EconomicResult | None:
        existing = await self.get_for_analysis(analysis_id, user_id)
        if existing is None:
            return None
        existing.sensitivity = sensitivity
        await self.session.commit()
        await self.session.refresh(existing)
        return existing
