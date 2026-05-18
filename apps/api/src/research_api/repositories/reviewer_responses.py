"""Phase 12 — Reviewer-response repository.

Many rows per project (typically one per reviewer). Each row stores the
full segmented + drafted JSON list in `comments`.
"""
from __future__ import annotations

from typing import Any, Protocol

from sqlalchemy import delete as sa_delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import ReviewerResponse, new_id


class ReviewerResponseRepository(Protocol):
    async def list_for_project(
        self, *, project_id: str, user_id: str
    ) -> list[ReviewerResponse]: ...
    async def get(
        self, response_id: str, user_id: str
    ) -> ReviewerResponse | None: ...
    async def create(
        self,
        *,
        project_id: str,
        user_id: str,
        reviewer_label: str,
        comments: list[dict[str, Any]],
    ) -> ReviewerResponse: ...
    async def update(
        self,
        response_id: str,
        user_id: str,
        *,
        reviewer_label: str | None = None,
        comments: list[dict[str, Any]] | None = None,
    ) -> ReviewerResponse | None: ...
    async def delete(
        self, response_id: str, user_id: str
    ) -> ReviewerResponse | None: ...


class SqliteReviewerResponseRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_project(
        self, *, project_id: str, user_id: str
    ) -> list[ReviewerResponse]:
        stmt = (
            select(ReviewerResponse)
            .where(
                ReviewerResponse.project_id == project_id,
                ReviewerResponse.user_id == user_id,
            )
            .order_by(ReviewerResponse.created_at.asc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get(
        self, response_id: str, user_id: str
    ) -> ReviewerResponse | None:
        stmt = select(ReviewerResponse).where(
            ReviewerResponse.id == response_id,
            ReviewerResponse.user_id == user_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def create(
        self,
        *,
        project_id: str,
        user_id: str,
        reviewer_label: str,
        comments: list[dict[str, Any]],
    ) -> ReviewerResponse:
        row = ReviewerResponse(
            id=new_id(),
            user_id=user_id,
            project_id=project_id,
            reviewer_label=reviewer_label,
            comments=list(comments or []),
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def update(
        self,
        response_id: str,
        user_id: str,
        *,
        reviewer_label: str | None = None,
        comments: list[dict[str, Any]] | None = None,
    ) -> ReviewerResponse | None:
        existing = await self.get(response_id, user_id)
        if existing is None:
            return None
        if reviewer_label is not None:
            existing.reviewer_label = reviewer_label
        if comments is not None:
            existing.comments = list(comments)
        await self.session.commit()
        await self.session.refresh(existing)
        return existing

    async def delete(
        self, response_id: str, user_id: str
    ) -> ReviewerResponse | None:
        existing = await self.get(response_id, user_id)
        if existing is None:
            return None
        await self.session.execute(
            sa_delete(ReviewerResponse).where(
                ReviewerResponse.id == response_id,
                ReviewerResponse.user_id == user_id,
            )
        )
        await self.session.commit()
        return existing
