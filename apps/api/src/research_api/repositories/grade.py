"""Phase 14 (MP14) — GRADE assessment repository.

Stateful side-effects only — the certainty derivation itself lives in
``services.review.grade``. Repo accepts a pre-computed ``certainty`` value
so the route layer drives the algorithm.
"""
from __future__ import annotations

from typing import Protocol

from sqlalchemy import delete as sa_delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import GradeAssessment, new_id
from ..schemas.grade import GradeAssessmentCreate, GradeAssessmentUpdate


class GradeRepository(Protocol):
    async def list_for_review(
        self, review_id: str, user_id: str
    ) -> list[GradeAssessment]: ...
    async def get(self, grade_id: str, user_id: str) -> GradeAssessment | None: ...
    async def upsert(
        self,
        *,
        project_id: str,
        review_id: str,
        data: GradeAssessmentCreate,
        certainty: str,
        user_id: str,
    ) -> GradeAssessment: ...
    async def update(
        self,
        grade_id: str,
        patch: GradeAssessmentUpdate,
        certainty: str | None,
        user_id: str,
    ) -> GradeAssessment | None: ...
    async def delete(self, grade_id: str, user_id: str) -> bool: ...


class SqliteGradeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_review(
        self, review_id: str, user_id: str
    ) -> list[GradeAssessment]:
        stmt = (
            select(GradeAssessment)
            .where(
                GradeAssessment.review_id == review_id,
                GradeAssessment.user_id == user_id,
            )
            .order_by(GradeAssessment.created_at.asc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get(self, grade_id: str, user_id: str) -> GradeAssessment | None:
        stmt = select(GradeAssessment).where(
            GradeAssessment.id == grade_id,
            GradeAssessment.user_id == user_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_by_outcome(
        self, review_id: str, outcome_label: str, user_id: str
    ) -> GradeAssessment | None:
        stmt = select(GradeAssessment).where(
            GradeAssessment.review_id == review_id,
            GradeAssessment.outcome_label == outcome_label,
            GradeAssessment.user_id == user_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def upsert(
        self,
        *,
        project_id: str,
        review_id: str,
        data: GradeAssessmentCreate,
        certainty: str,
        user_id: str,
    ) -> GradeAssessment:
        existing = await self.get_by_outcome(review_id, data.outcome_label, user_id)
        if existing is not None:
            existing.starting_certainty = data.starting_certainty
            existing.domain_risk_of_bias = data.domain_risk_of_bias
            existing.domain_inconsistency = data.domain_inconsistency
            existing.domain_indirectness = data.domain_indirectness
            existing.domain_imprecision = data.domain_imprecision
            existing.domain_publication_bias = data.domain_publication_bias
            existing.upgrade_large_effect = data.upgrade_large_effect
            existing.upgrade_dose_response = data.upgrade_dose_response
            existing.upgrade_confounders_against = data.upgrade_confounders_against
            existing.notes = data.notes
            existing.meta_id = data.meta_id
            existing.certainty = certainty
            await self.session.commit()
            await self.session.refresh(existing)
            return existing

        row = GradeAssessment(
            id=new_id(),
            user_id=user_id,
            project_id=project_id,
            review_id=review_id,
            meta_id=data.meta_id,
            outcome_label=data.outcome_label,
            starting_certainty=data.starting_certainty,
            domain_risk_of_bias=data.domain_risk_of_bias,
            domain_inconsistency=data.domain_inconsistency,
            domain_indirectness=data.domain_indirectness,
            domain_imprecision=data.domain_imprecision,
            domain_publication_bias=data.domain_publication_bias,
            upgrade_large_effect=data.upgrade_large_effect,
            upgrade_dose_response=data.upgrade_dose_response,
            upgrade_confounders_against=data.upgrade_confounders_against,
            certainty=certainty,
            notes=data.notes,
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def update(
        self,
        grade_id: str,
        patch: GradeAssessmentUpdate,
        certainty: str | None,
        user_id: str,
    ) -> GradeAssessment | None:
        row = await self.get(grade_id, user_id)
        if row is None:
            return None
        payload = patch.model_dump(exclude_unset=True)
        for key, val in payload.items():
            setattr(row, key, val)
        if certainty is not None:
            row.certainty = certainty
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def delete(self, grade_id: str, user_id: str) -> bool:
        row = await self.get(grade_id, user_id)
        if row is None:
            return False
        await self.session.execute(
            sa_delete(GradeAssessment).where(
                GradeAssessment.id == grade_id,
                GradeAssessment.user_id == user_id,
            )
        )
        await self.session.commit()
        return True
