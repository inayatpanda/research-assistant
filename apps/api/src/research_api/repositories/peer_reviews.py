"""Phase 4.6 — Repository for AI peer reviews."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Protocol

from sqlalchemy import delete as sa_delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import PeerReview, new_id


class PeerReviewRepository(Protocol):
    async def list_for_project(
        self, project_id: str, user_id: str
    ) -> list[PeerReview]: ...
    async def get(self, peer_review_id: str, user_id: str) -> PeerReview | None: ...
    async def create_pending(
        self,
        *,
        project_id: str,
        user_id: str,
        source_type: str,
        source_title: str,
        source_file_ref: dict[str, Any] | None,
        manuscript_snapshot: dict[str, Any] | None,
        ai_model: str,
    ) -> PeerReview: ...
    async def mark_completed(
        self,
        *,
        peer_review_id: str,
        user_id: str,
        critique: dict[str, Any],
        recommendation: str,
        ai_model: str,
    ) -> PeerReview | None: ...
    async def mark_failed(
        self,
        *,
        peer_review_id: str,
        user_id: str,
        error: str,
    ) -> PeerReview | None: ...
    async def delete(self, peer_review_id: str, user_id: str) -> bool: ...


class SqlitePeerReviewRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_project(
        self, project_id: str, user_id: str
    ) -> list[PeerReview]:
        stmt = (
            select(PeerReview)
            .where(
                PeerReview.project_id == project_id,
                PeerReview.user_id == user_id,
            )
            .order_by(PeerReview.created_at.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get(
        self, peer_review_id: str, user_id: str
    ) -> PeerReview | None:
        stmt = select(PeerReview).where(
            PeerReview.id == peer_review_id,
            PeerReview.user_id == user_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def create_pending(
        self,
        *,
        project_id: str,
        user_id: str,
        source_type: str,
        source_title: str,
        source_file_ref: dict[str, Any] | None,
        manuscript_snapshot: dict[str, Any] | None,
        ai_model: str,
    ) -> PeerReview:
        row = PeerReview(
            id=new_id(),
            user_id=user_id,
            project_id=project_id,
            source_type=source_type,
            source_file_ref=source_file_ref,
            source_title=source_title[:1000],
            manuscript_snapshot=manuscript_snapshot,
            critique={},
            recommendation="major_revision",
            ai_model=ai_model,
            status="pending",
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def mark_completed(
        self,
        *,
        peer_review_id: str,
        user_id: str,
        critique: dict[str, Any],
        recommendation: str,
        ai_model: str,
    ) -> PeerReview | None:
        row = await self.get(peer_review_id, user_id)
        if row is None:
            return None
        row.critique = critique
        row.recommendation = recommendation
        row.ai_model = ai_model
        row.status = "completed"
        row.error = None
        row.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def mark_failed(
        self,
        *,
        peer_review_id: str,
        user_id: str,
        error: str,
    ) -> PeerReview | None:
        row = await self.get(peer_review_id, user_id)
        if row is None:
            return None
        row.status = "failed"
        row.error = error[:2000]
        row.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def delete(self, peer_review_id: str, user_id: str) -> bool:
        row = await self.get(peer_review_id, user_id)
        if row is None:
            return False
        await self.session.execute(
            sa_delete(PeerReview).where(
                PeerReview.id == peer_review_id,
                PeerReview.user_id == user_id,
            )
        )
        await self.session.commit()
        return True
