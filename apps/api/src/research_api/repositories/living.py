"""Phase 15 (MP15) — Living-review job + hit repository."""
from __future__ import annotations

from typing import Protocol

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import LivingReviewHit, LivingReviewJob, new_id


class LivingReviewRepository(Protocol):
    async def get_for_review(
        self, review_id: str, user_id: str
    ) -> LivingReviewJob | None: ...
    async def get(self, job_id: str, user_id: str) -> LivingReviewJob | None: ...
    async def upsert(
        self,
        *,
        project_id: str,
        review_id: str,
        pubmed_query: str,
        schedule: str,
        enabled: bool,
        user_id: str,
    ) -> LivingReviewJob: ...
    async def update_fields(
        self,
        *,
        job_id: str,
        user_id: str,
        pubmed_query: str | None,
        schedule: str | None,
        enabled: bool | None,
    ) -> LivingReviewJob | None: ...
    async def delete(self, job_id: str, user_id: str) -> bool: ...
    async def list_hits(
        self,
        *,
        job_id: str,
        user_id: str,
        decision: str | None,
    ) -> list[LivingReviewHit]: ...
    async def get_hit(
        self, hit_id: str, user_id: str
    ) -> LivingReviewHit | None: ...
    async def update_hit_decision(
        self, hit_id: str, user_id: str, decision: str
    ) -> LivingReviewHit | None: ...


class SqliteLivingReviewRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_for_review(
        self, review_id: str, user_id: str
    ) -> LivingReviewJob | None:
        stmt = select(LivingReviewJob).where(
            LivingReviewJob.review_id == review_id,
            LivingReviewJob.user_id == user_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get(self, job_id: str, user_id: str) -> LivingReviewJob | None:
        stmt = select(LivingReviewJob).where(
            LivingReviewJob.id == job_id,
            LivingReviewJob.user_id == user_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def upsert(
        self,
        *,
        project_id: str,
        review_id: str,
        pubmed_query: str,
        schedule: str,
        enabled: bool,
        user_id: str,
    ) -> LivingReviewJob:
        existing = await self.get_for_review(review_id, user_id)
        if existing is None:
            row = LivingReviewJob(
                id=new_id(),
                user_id=user_id,
                project_id=project_id,
                review_id=review_id,
                pubmed_query=pubmed_query,
                schedule=schedule,
                enabled=enabled,
            )
            self.session.add(row)
            await self.session.commit()
            await self.session.refresh(row)
            return row
        existing.pubmed_query = pubmed_query
        existing.schedule = schedule
        existing.enabled = enabled
        await self.session.commit()
        await self.session.refresh(existing)
        return existing

    async def update_fields(
        self,
        *,
        job_id: str,
        user_id: str,
        pubmed_query: str | None,
        schedule: str | None,
        enabled: bool | None,
    ) -> LivingReviewJob | None:
        row = await self.get(job_id, user_id)
        if row is None:
            return None
        if pubmed_query is not None:
            row.pubmed_query = pubmed_query
        if schedule is not None:
            row.schedule = schedule
        if enabled is not None:
            row.enabled = enabled
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def delete(self, job_id: str, user_id: str) -> bool:
        row = await self.get(job_id, user_id)
        if row is None:
            return False
        await self.session.delete(row)
        await self.session.commit()
        return True

    async def list_hits(
        self,
        *,
        job_id: str,
        user_id: str,
        decision: str | None,
    ) -> list[LivingReviewHit]:
        stmt = (
            select(LivingReviewHit)
            .where(
                LivingReviewHit.job_id == job_id,
                LivingReviewHit.user_id == user_id,
            )
            .order_by(LivingReviewHit.run_at.desc(), LivingReviewHit.id.desc())
        )
        if decision is not None:
            stmt = stmt.where(LivingReviewHit.decision == decision)
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_hit(
        self, hit_id: str, user_id: str
    ) -> LivingReviewHit | None:
        stmt = select(LivingReviewHit).where(
            LivingReviewHit.id == hit_id,
            LivingReviewHit.user_id == user_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def update_hit_decision(
        self, hit_id: str, user_id: str, decision: str
    ) -> LivingReviewHit | None:
        row = await self.get_hit(hit_id, user_id)
        if row is None:
            return None
        row.decision = decision
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def delete_hits_for_job(self, job_id: str) -> None:
        await self.session.execute(
            delete(LivingReviewHit).where(LivingReviewHit.job_id == job_id)
        )
        await self.session.commit()


__all__ = ["LivingReviewRepository", "SqliteLivingReviewRepository"]
