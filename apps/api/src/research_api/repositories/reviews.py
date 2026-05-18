from __future__ import annotations

from typing import Any, Protocol

from sqlalchemy import delete as sa_delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import (
    Article,
    ExtractionRecord,
    Review,
    RobAssessment,
    ScreeningRecord,
    SearchRecord,
    new_id,
)
from ..schemas.review import (
    ExtractionRecordCreate,
    ExtractionRecordUpdate,
    ReviewUpdate,
    RoBAssessmentCreate,
    RoBAssessmentUpdate,
    ScreeningRecordCreate,
    ScreeningRecordUpdate,
    SearchRecordCreate,
    SearchRecordUpdate,
)


class ReviewRepository(Protocol):
    async def get_or_create(self, *, project_id: str, user_id: str) -> Review: ...
    async def get(self, review_id: str, user_id: str) -> Review | None: ...
    async def get_by_project(self, project_id: str, user_id: str) -> Review | None: ...
    async def update(
        self, review_id: str, patch: ReviewUpdate, user_id: str
    ) -> Review | None: ...

    async def list_search(self, review_id: str, user_id: str) -> list[SearchRecord]: ...
    async def get_search(self, search_id: str, user_id: str) -> SearchRecord | None: ...
    async def create_search(
        self, *, review_id: str, data: SearchRecordCreate, user_id: str
    ) -> SearchRecord: ...
    async def update_search(
        self, search_id: str, patch: SearchRecordUpdate, user_id: str
    ) -> SearchRecord | None: ...
    async def delete_search(self, search_id: str, user_id: str) -> None: ...

    async def list_screening(
        self, review_id: str, user_id: str, *, stage: str | None = None
    ) -> list[ScreeningRecord]: ...
    async def get_screening(
        self, screening_id: str, user_id: str
    ) -> ScreeningRecord | None: ...
    async def upsert_screening(
        self, *, review_id: str, data: ScreeningRecordCreate, user_id: str
    ) -> ScreeningRecord: ...
    async def update_screening(
        self, screening_id: str, patch: ScreeningRecordUpdate, user_id: str
    ) -> ScreeningRecord | None: ...
    async def set_ai_suggestion(
        self, screening_id: str, suggestion: dict[str, Any], user_id: str
    ) -> ScreeningRecord | None: ...
    async def delete_screening(self, screening_id: str, user_id: str) -> None: ...

    async def list_rob(self, review_id: str, user_id: str) -> list[RobAssessment]: ...
    async def get_rob(self, rob_id: str, user_id: str) -> RobAssessment | None: ...
    async def upsert_rob(
        self,
        *,
        review_id: str,
        data: RoBAssessmentCreate,
        overall_auto: str,
        overall_override: str | None,
        user_id: str,
    ) -> RobAssessment: ...
    async def update_rob(
        self,
        rob_id: str,
        patch: RoBAssessmentUpdate,
        overall_auto: str | None,
        user_id: str,
    ) -> RobAssessment | None: ...
    async def delete_rob(self, rob_id: str, user_id: str) -> None: ...

    async def list_extraction(
        self, review_id: str, user_id: str
    ) -> list[ExtractionRecord]: ...
    async def get_extraction(
        self, ext_id: str, user_id: str
    ) -> ExtractionRecord | None: ...
    async def upsert_extraction(
        self, *, review_id: str, data: ExtractionRecordCreate, user_id: str
    ) -> ExtractionRecord: ...
    async def update_extraction(
        self, ext_id: str, patch: ExtractionRecordUpdate, user_id: str
    ) -> ExtractionRecord | None: ...
    async def delete_extraction(self, ext_id: str, user_id: str) -> None: ...


class ScreeningArticleMismatch(Exception):
    """Raised when a screening row references an article outside the review's project."""


class SqliteReviewRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ── Review ──────────────────────────────────────────────────────────
    async def get_or_create(self, *, project_id: str, user_id: str) -> Review:
        existing = await self.get_by_project(project_id, user_id)
        if existing is not None:
            return existing
        row = Review(id=new_id(), user_id=user_id, project_id=project_id)
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def get(self, review_id: str, user_id: str) -> Review | None:
        stmt = select(Review).where(
            Review.id == review_id, Review.user_id == user_id
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_by_project(
        self, project_id: str, user_id: str
    ) -> Review | None:
        stmt = select(Review).where(
            Review.project_id == project_id, Review.user_id == user_id
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def update(
        self, review_id: str, patch: ReviewUpdate, user_id: str
    ) -> Review | None:
        existing = await self.get(review_id, user_id)
        if existing is None:
            return None
        for k, v in patch.model_dump(exclude_unset=True).items():
            setattr(existing, k, v)
        await self.session.commit()
        await self.session.refresh(existing)
        return existing

    # ── Search ──────────────────────────────────────────────────────────
    async def list_search(
        self, review_id: str, user_id: str
    ) -> list[SearchRecord]:
        stmt = (
            select(SearchRecord)
            .where(
                SearchRecord.review_id == review_id,
                SearchRecord.user_id == user_id,
            )
            .order_by(SearchRecord.date_searched.desc(), SearchRecord.created_at.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_search(
        self, search_id: str, user_id: str
    ) -> SearchRecord | None:
        stmt = select(SearchRecord).where(
            SearchRecord.id == search_id, SearchRecord.user_id == user_id
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def create_search(
        self, *, review_id: str, data: SearchRecordCreate, user_id: str
    ) -> SearchRecord:
        row = SearchRecord(
            id=new_id(),
            user_id=user_id,
            review_id=review_id,
            database_name=data.database_name,
            query_string=data.query_string,
            date_searched=data.date_searched,
            n_results=data.n_results,
            notes=data.notes,
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def update_search(
        self, search_id: str, patch: SearchRecordUpdate, user_id: str
    ) -> SearchRecord | None:
        existing = await self.get_search(search_id, user_id)
        if existing is None:
            return None
        for k, v in patch.model_dump(exclude_unset=True).items():
            setattr(existing, k, v)
        await self.session.commit()
        await self.session.refresh(existing)
        return existing

    async def delete_search(self, search_id: str, user_id: str) -> None:
        await self.session.execute(
            sa_delete(SearchRecord).where(
                SearchRecord.id == search_id,
                SearchRecord.user_id == user_id,
            )
        )
        await self.session.commit()

    # ── Screening ───────────────────────────────────────────────────────
    async def list_screening(
        self, review_id: str, user_id: str, *, stage: str | None = None
    ) -> list[ScreeningRecord]:
        stmt = select(ScreeningRecord).where(
            ScreeningRecord.review_id == review_id,
            ScreeningRecord.user_id == user_id,
        )
        if stage is not None:
            stmt = stmt.where(ScreeningRecord.stage == stage)
        stmt = stmt.order_by(ScreeningRecord.created_at.asc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_screening(
        self, screening_id: str, user_id: str
    ) -> ScreeningRecord | None:
        stmt = select(ScreeningRecord).where(
            ScreeningRecord.id == screening_id,
            ScreeningRecord.user_id == user_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def _get_review_by_id(self, review_id: str, user_id: str) -> Review | None:
        return await self.get(review_id, user_id)

    async def upsert_screening(
        self, *, review_id: str, data: ScreeningRecordCreate, user_id: str
    ) -> ScreeningRecord:
        review = await self._get_review_by_id(review_id, user_id)
        if review is None:
            raise ScreeningArticleMismatch("review not found for this user")
        article_stmt = select(Article).where(
            Article.id == data.article_id, Article.user_id == user_id
        )
        article = (await self.session.execute(article_stmt)).scalar_one_or_none()
        if article is None or article.project_id != review.project_id:
            raise ScreeningArticleMismatch(
                "article does not belong to the same project as the review"
            )

        existing_stmt = select(ScreeningRecord).where(
            ScreeningRecord.review_id == review_id,
            ScreeningRecord.user_id == user_id,
            ScreeningRecord.article_id == data.article_id,
            ScreeningRecord.stage == data.stage,
        )
        existing = (
            await self.session.execute(existing_stmt)
        ).scalar_one_or_none()
        if existing is not None:
            existing.decision = data.decision
            existing.exclusion_category = data.exclusion_category
            existing.reason = data.reason
            await self.session.commit()
            await self.session.refresh(existing)
            return existing

        row = ScreeningRecord(
            id=new_id(),
            user_id=user_id,
            review_id=review_id,
            article_id=data.article_id,
            stage=data.stage,
            decision=data.decision,
            exclusion_category=data.exclusion_category,
            reason=data.reason,
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def update_screening(
        self, screening_id: str, patch: ScreeningRecordUpdate, user_id: str
    ) -> ScreeningRecord | None:
        existing = await self.get_screening(screening_id, user_id)
        if existing is None:
            return None
        from datetime import datetime, timezone

        for k, v in patch.model_dump(exclude_unset=True).items():
            setattr(existing, k, v)
        if "decision" in patch.model_dump(exclude_unset=True):
            existing.decided_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(existing)
        return existing

    async def set_ai_suggestion(
        self, screening_id: str, suggestion: dict[str, Any], user_id: str
    ) -> ScreeningRecord | None:
        existing = await self.get_screening(screening_id, user_id)
        if existing is None:
            return None
        existing.ai_suggestion = suggestion
        await self.session.commit()
        await self.session.refresh(existing)
        return existing

    async def delete_screening(self, screening_id: str, user_id: str) -> None:
        await self.session.execute(
            sa_delete(ScreeningRecord).where(
                ScreeningRecord.id == screening_id,
                ScreeningRecord.user_id == user_id,
            )
        )
        await self.session.commit()

    # ── RoB ─────────────────────────────────────────────────────────────
    async def list_rob(
        self, review_id: str, user_id: str
    ) -> list[RobAssessment]:
        stmt = (
            select(RobAssessment)
            .where(
                RobAssessment.review_id == review_id,
                RobAssessment.user_id == user_id,
            )
            .order_by(RobAssessment.created_at.asc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_rob(self, rob_id: str, user_id: str) -> RobAssessment | None:
        stmt = select(RobAssessment).where(
            RobAssessment.id == rob_id, RobAssessment.user_id == user_id
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def upsert_rob(
        self,
        *,
        review_id: str,
        data: RoBAssessmentCreate,
        overall_auto: str,
        overall_override: str | None,
        user_id: str,
    ) -> RobAssessment:
        existing_stmt = select(RobAssessment).where(
            RobAssessment.review_id == review_id,
            RobAssessment.user_id == user_id,
            RobAssessment.article_id == data.article_id,
            RobAssessment.tool == data.tool,
        )
        existing = (await self.session.execute(existing_stmt)).scalar_one_or_none()
        if existing is not None:
            existing.domain_answers = data.domain_answers
            existing.overall_auto = overall_auto
            existing.overall_override = overall_override
            existing.notes = data.notes
            await self.session.commit()
            await self.session.refresh(existing)
            return existing

        row = RobAssessment(
            id=new_id(),
            user_id=user_id,
            review_id=review_id,
            article_id=data.article_id,
            tool=data.tool,
            domain_answers=data.domain_answers,
            overall_auto=overall_auto,
            overall_override=overall_override,
            notes=data.notes,
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def update_rob(
        self,
        rob_id: str,
        patch: RoBAssessmentUpdate,
        overall_auto: str | None,
        user_id: str,
    ) -> RobAssessment | None:
        existing = await self.get_rob(rob_id, user_id)
        if existing is None:
            return None
        patch_dict = patch.model_dump(exclude_unset=True)
        if "domain_answers" in patch_dict and patch_dict["domain_answers"] is not None:
            existing.domain_answers = patch_dict["domain_answers"]
            if overall_auto is not None:
                existing.overall_auto = overall_auto
        if "overall_override" in patch_dict:
            existing.overall_override = patch_dict["overall_override"]
        if "notes" in patch_dict:
            existing.notes = patch_dict["notes"]
        await self.session.commit()
        await self.session.refresh(existing)
        return existing

    async def delete_rob(self, rob_id: str, user_id: str) -> None:
        await self.session.execute(
            sa_delete(RobAssessment).where(
                RobAssessment.id == rob_id,
                RobAssessment.user_id == user_id,
            )
        )
        await self.session.commit()

    # ── Extraction ──────────────────────────────────────────────────────
    async def list_extraction(
        self, review_id: str, user_id: str
    ) -> list[ExtractionRecord]:
        stmt = (
            select(ExtractionRecord)
            .where(
                ExtractionRecord.review_id == review_id,
                ExtractionRecord.user_id == user_id,
            )
            .order_by(ExtractionRecord.created_at.asc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_extraction(
        self, ext_id: str, user_id: str
    ) -> ExtractionRecord | None:
        stmt = select(ExtractionRecord).where(
            ExtractionRecord.id == ext_id,
            ExtractionRecord.user_id == user_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def upsert_extraction(
        self, *, review_id: str, data: ExtractionRecordCreate, user_id: str
    ) -> ExtractionRecord:
        existing_stmt = select(ExtractionRecord).where(
            ExtractionRecord.review_id == review_id,
            ExtractionRecord.user_id == user_id,
            ExtractionRecord.article_id == data.article_id,
        )
        existing = (await self.session.execute(existing_stmt)).scalar_one_or_none()
        if existing is not None:
            existing.fields = data.fields
            await self.session.commit()
            await self.session.refresh(existing)
            return existing
        row = ExtractionRecord(
            id=new_id(),
            user_id=user_id,
            review_id=review_id,
            article_id=data.article_id,
            fields=data.fields,
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def update_extraction(
        self, ext_id: str, patch: ExtractionRecordUpdate, user_id: str
    ) -> ExtractionRecord | None:
        existing = await self.get_extraction(ext_id, user_id)
        if existing is None:
            return None
        existing.fields = patch.fields
        await self.session.commit()
        await self.session.refresh(existing)
        return existing

    async def delete_extraction(self, ext_id: str, user_id: str) -> None:
        await self.session.execute(
            sa_delete(ExtractionRecord).where(
                ExtractionRecord.id == ext_id,
                ExtractionRecord.user_id == user_id,
            )
        )
        await self.session.commit()
