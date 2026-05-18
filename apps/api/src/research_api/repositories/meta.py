"""Repository for meta-analyses + per-study inputs."""
from __future__ import annotations

from typing import Any, Protocol, Sequence

from sqlalchemy import delete as sa_delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Article, MetaAnalysis, MetaInput, Review, new_id
from ..schemas.meta import (
    MetaAnalysisCreate,
    MetaAnalysisUpdate,
    MetaInputCreate,
    MetaInputUpdate,
)
from ..services.meta.heterogeneity import Heterogeneity
from ..services.meta.pooling import PooledResult


class MetaArticleMismatch(Exception):
    """Raised when a meta input references an article outside the meta's review's project."""


_INPUT_FIELDS = (
    "study_label",
    "mean_a", "sd_a", "n_a", "mean_b", "sd_b", "n_b",
    "events_a", "n_a_total", "events_b", "n_b_total",
    "log_hr", "se_log_hr", "hr", "hr_ci_low", "hr_ci_high",
    "r", "n_r",
)


class MetaRepository(Protocol):
    async def list(self, *, review_id: str, user_id: str) -> list[MetaAnalysis]: ...
    async def get(self, meta_id: str, user_id: str) -> MetaAnalysis | None: ...
    async def get_with_inputs(
        self, meta_id: str, user_id: str
    ) -> tuple[MetaAnalysis, list[MetaInput]] | None: ...
    async def create(
        self, *, review_id: str, data: MetaAnalysisCreate, user_id: str
    ) -> MetaAnalysis: ...
    async def update(
        self, meta_id: str, patch: MetaAnalysisUpdate, user_id: str
    ) -> MetaAnalysis | None: ...
    async def delete(self, meta_id: str, user_id: str) -> bool: ...

    async def list_inputs(self, meta_id: str, user_id: str) -> list[MetaInput]: ...
    async def upsert_input(
        self, *, meta_id: str, data: MetaInputCreate, user_id: str
    ) -> MetaInput: ...
    async def update_input(
        self, input_id: str, patch: MetaInputUpdate, user_id: str
    ) -> MetaInput | None: ...
    async def delete_input(self, input_id: str, user_id: str) -> bool: ...

    async def write_pooled(
        self, *, meta_id: str, user_id: str,
        pooled: PooledResult, heterogeneity: Heterogeneity,
        subgroup_summary: dict | None,
    ) -> MetaAnalysis | None: ...
    async def write_interpretation(
        self, *, meta_id: str, user_id: str, prose: str
    ) -> MetaAnalysis | None: ...
    async def set_status(self, *, meta_id: str, user_id: str, status: str) -> None: ...


class SqliteMetaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _get_review_for_meta(self, meta: MetaAnalysis, user_id: str) -> Review | None:
        stmt = select(Review).where(Review.id == meta.review_id, Review.user_id == user_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def _verify_article_in_project(
        self, article_id: str, project_id: str, user_id: str
    ) -> Article:
        stmt = select(Article).where(
            Article.id == article_id,
            Article.user_id == user_id,
        )
        art = (await self.session.execute(stmt)).scalar_one_or_none()
        if art is None or art.project_id != project_id:
            raise MetaArticleMismatch(
                f"article {article_id!r} not in the meta-analysis project"
            )
        return art

    async def list(self, *, review_id: str, user_id: str) -> list[MetaAnalysis]:
        stmt = (
            select(MetaAnalysis)
            .where(MetaAnalysis.review_id == review_id, MetaAnalysis.user_id == user_id)
            .order_by(MetaAnalysis.created_at.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get(self, meta_id: str, user_id: str) -> MetaAnalysis | None:
        stmt = select(MetaAnalysis).where(
            MetaAnalysis.id == meta_id, MetaAnalysis.user_id == user_id
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_inputs(self, meta_id: str, user_id: str) -> list[MetaInput]:
        stmt = (
            select(MetaInput)
            .where(MetaInput.meta_id == meta_id, MetaInput.user_id == user_id)
            .order_by(MetaInput.created_at.asc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_with_inputs(
        self, meta_id: str, user_id: str
    ) -> tuple[MetaAnalysis, list[MetaInput]] | None:
        meta = await self.get(meta_id, user_id)
        if meta is None:
            return None
        inputs = await self.list_inputs(meta_id, user_id)
        return meta, inputs

    async def create(
        self, *, review_id: str, data: MetaAnalysisCreate, user_id: str
    ) -> MetaAnalysis:
        # Verify review exists for user
        rev_stmt = select(Review).where(Review.id == review_id, Review.user_id == user_id)
        review = (await self.session.execute(rev_stmt)).scalar_one_or_none()
        if review is None:
            raise MetaArticleMismatch("review not found for this user")

        meta = MetaAnalysis(
            id=new_id(),
            user_id=user_id,
            review_id=review_id,
            title=data.title,
            effect_metric=data.effect_metric,
            model=data.model,
            subgroup_variable=data.subgroup_variable,
            status="draft",
        )
        self.session.add(meta)
        await self.session.flush()

        for inp_data in data.inputs:
            await self._verify_article_in_project(
                inp_data.article_id, review.project_id, user_id
            )
            inp = MetaInput(
                id=new_id(),
                user_id=user_id,
                meta_id=meta.id,
                article_id=inp_data.article_id,
            )
            for f in _INPUT_FIELDS:
                setattr(inp, f, getattr(inp_data, f))
            self.session.add(inp)
        await self.session.commit()
        await self.session.refresh(meta)
        return meta

    async def update(
        self, meta_id: str, patch: MetaAnalysisUpdate, user_id: str
    ) -> MetaAnalysis | None:
        existing = await self.get(meta_id, user_id)
        if existing is None:
            return None
        patch_dict = patch.model_dump(exclude_unset=True)
        for k, v in patch_dict.items():
            setattr(existing, k, v)
        # Updating the metric or model invalidates the pooled numerics
        if any(k in patch_dict for k in ("effect_metric", "model", "subgroup_variable")):
            existing.status = "draft"
            existing.pooled_estimate = None
            existing.pooled_se = None
            existing.ci_low = None
            existing.ci_high = None
            existing.z_value = None
            existing.p_value = None
            existing.q_value = None
            existing.q_df = None
            existing.q_p = None
            existing.i2 = None
            existing.tau2 = None
            existing.subgroup_summary = None
            existing.ai_interpretation = None
        await self.session.commit()
        await self.session.refresh(existing)
        return existing

    async def delete(self, meta_id: str, user_id: str) -> bool:
        existing = await self.get(meta_id, user_id)
        if existing is None:
            return False
        # Manually cascade for SQLite-FK-off safety
        await self.session.execute(
            sa_delete(MetaInput).where(
                MetaInput.meta_id == meta_id, MetaInput.user_id == user_id
            )
        )
        await self.session.execute(
            sa_delete(MetaAnalysis).where(
                MetaAnalysis.id == meta_id, MetaAnalysis.user_id == user_id
            )
        )
        await self.session.commit()
        return True

    async def upsert_input(
        self, *, meta_id: str, data: MetaInputCreate, user_id: str
    ) -> MetaInput:
        meta = await self.get(meta_id, user_id)
        if meta is None:
            raise MetaArticleMismatch("meta-analysis not found for this user")
        review = await self._get_review_for_meta(meta, user_id)
        if review is None:
            raise MetaArticleMismatch("review not found for this user")
        await self._verify_article_in_project(data.article_id, review.project_id, user_id)

        stmt = select(MetaInput).where(
            MetaInput.meta_id == meta_id,
            MetaInput.user_id == user_id,
            MetaInput.article_id == data.article_id,
        )
        existing = (await self.session.execute(stmt)).scalar_one_or_none()
        if existing is not None:
            for f in _INPUT_FIELDS:
                setattr(existing, f, getattr(data, f))
            await self.session.commit()
            await self.session.refresh(existing)
            return existing
        row = MetaInput(
            id=new_id(),
            user_id=user_id,
            meta_id=meta_id,
            article_id=data.article_id,
        )
        for f in _INPUT_FIELDS:
            setattr(row, f, getattr(data, f))
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def update_input(
        self, input_id: str, patch: MetaInputUpdate, user_id: str
    ) -> MetaInput | None:
        stmt = select(MetaInput).where(
            MetaInput.id == input_id, MetaInput.user_id == user_id
        )
        existing = (await self.session.execute(stmt)).scalar_one_or_none()
        if existing is None:
            return None
        for k, v in patch.model_dump(exclude_unset=True).items():
            setattr(existing, k, v)
        await self.session.commit()
        await self.session.refresh(existing)
        return existing

    async def delete_input(self, input_id: str, user_id: str) -> bool:
        result = await self.session.execute(
            sa_delete(MetaInput).where(
                MetaInput.id == input_id, MetaInput.user_id == user_id
            )
        )
        await self.session.commit()
        return result.rowcount > 0

    async def write_pooled(
        self, *, meta_id: str, user_id: str,
        pooled: PooledResult, heterogeneity: Heterogeneity,
        subgroup_summary: dict | None,
    ) -> MetaAnalysis | None:
        existing = await self.get(meta_id, user_id)
        if existing is None:
            return None
        existing.pooled_estimate = pooled.estimate
        existing.pooled_se = pooled.se
        existing.ci_low = pooled.ci_low
        existing.ci_high = pooled.ci_high
        existing.z_value = pooled.z
        existing.p_value = pooled.p
        existing.q_value = heterogeneity.q
        existing.q_df = heterogeneity.df
        existing.q_p = heterogeneity.p
        existing.i2 = heterogeneity.i2
        existing.tau2 = heterogeneity.tau2
        existing.subgroup_summary = subgroup_summary
        existing.status = "completed"
        await self.session.commit()
        await self.session.refresh(existing)
        return existing

    async def write_interpretation(
        self, *, meta_id: str, user_id: str, prose: str
    ) -> MetaAnalysis | None:
        existing = await self.get(meta_id, user_id)
        if existing is None:
            return None
        existing.ai_interpretation = prose
        await self.session.commit()
        await self.session.refresh(existing)
        return existing

    async def set_status(self, *, meta_id: str, user_id: str, status: str) -> None:
        existing = await self.get(meta_id, user_id)
        if existing is None:
            return
        existing.status = status
        await self.session.commit()

    async def set_input_subgroup(self, *, input_id: str, user_id: str, subgroup: str | None) -> None:
        stmt = select(MetaInput).where(
            MetaInput.id == input_id, MetaInput.user_id == user_id
        )
        existing = (await self.session.execute(stmt)).scalar_one_or_none()
        if existing is None:
            return
        existing.subgroup = subgroup
        await self.session.commit()
