"""Phase 14 (MP14) — PROSPERO registration draft routes.

Endpoints:

  GET    /projects/{pid}/review/prospero          auto-creates draft if absent
  PATCH  /projects/{pid}/review/prospero          partial-merge fields
  POST   /projects/{pid}/review/prospero/export   text/plain copy-paste block
"""
from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from ..container import Container, get_container
from ..auth_deps import get_current_user
from ..schemas.auth import UserRead
from ..repositories.projects import SqliteProjectRepository
from ..repositories.prospero import SqliteProsperoRepository
from ..repositories.reviews import SqliteReviewRepository
from ..schemas.prospero import ProsperoDraftPatch, ProsperoDraftRead
from ..services.review.prospero import default_draft, format_for_export

router = APIRouter(tags=["prospero"])


async def _session(
    container: Container = Depends(get_container),
) -> AsyncIterator[AsyncSession]:
    async with container.session_factory() as s:
        yield s


def _user_id(user: UserRead = Depends(get_current_user)) -> str:
    # Phase S1 — delegate to the real session-derived user. The legacy
    # static-id flow remains available via ``RMA_DISABLE_AUTH=1``.
    return user.id


async def _resolve(project_id: str, session: AsyncSession, user_id: str):
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    review_repo = SqliteReviewRepository(session)
    review = await review_repo.get_or_create(
        project_id=project_id, user_id=user_id
    )
    return project, review, review_repo


@router.get(
    "/projects/{project_id}/review/prospero",
    response_model=ProsperoDraftRead,
)
async def get_prospero(
    project_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> ProsperoDraftRead:
    project, review, review_repo = await _resolve(project_id, session, user_id)
    repo = SqliteProsperoRepository(session)
    row = await repo.get(review.id, user_id)
    if row is None:
        search_records = await review_repo.list_search(review.id, user_id)
        fields = default_draft(
            review,
            project=project,
            search_records=search_records,
        )
        row = await repo.create(
            project_id=project_id,
            review_id=review.id,
            fields=fields,
            user_id=user_id,
        )
    return ProsperoDraftRead.model_validate(row)


@router.patch(
    "/projects/{project_id}/review/prospero",
    response_model=ProsperoDraftRead,
)
async def patch_prospero(
    project_id: str,
    body: ProsperoDraftPatch,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> ProsperoDraftRead:
    project, review, review_repo = await _resolve(project_id, session, user_id)
    repo = SqliteProsperoRepository(session)
    row = await repo.get(review.id, user_id)
    if row is None:
        # Bootstrap the draft on first patch so we don't 404 on a fresh review.
        search_records = await review_repo.list_search(review.id, user_id)
        fields = default_draft(
            review,
            project=project,
            search_records=search_records,
        )
        row = await repo.create(
            project_id=project_id,
            review_id=review.id,
            fields=fields,
            user_id=user_id,
        )
    updated = await repo.update_fields(
        review_id=review.id,
        merge=body.fields,
        user_id=user_id,
    )
    return ProsperoDraftRead.model_validate(updated or row)


@router.post("/projects/{project_id}/review/prospero/export")
async def export_prospero(
    project_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> Response:
    project, review, review_repo = await _resolve(project_id, session, user_id)
    repo = SqliteProsperoRepository(session)
    row = await repo.get(review.id, user_id)
    if row is None:
        search_records = await review_repo.list_search(review.id, user_id)
        fields = default_draft(
            review,
            project=project,
            search_records=search_records,
        )
        row = await repo.create(
            project_id=project_id,
            review_id=review.id,
            fields=fields,
            user_id=user_id,
        )
    text = format_for_export(row.fields)
    return Response(
        content=text,
        media_type="text/plain",
        headers={"Cache-Control": "no-store"},
    )
