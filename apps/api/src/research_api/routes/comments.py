"""Phase 11 — Manuscript margin-comment routes.

Endpoints (under /api/projects/{project_id}/comments):

  GET    /                       list (filterable by ?section=&resolved=)
  POST   /                       create
  PATCH  /{comment_id}            update body and/or resolved
  DELETE /{comment_id}            delete
"""
from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..container import Container, get_container
from ..auth_deps import get_current_user
from ..schemas.auth import UserRead
from ..repositories.comments import SqliteCommentRepository
from ..repositories.projects import SqliteProjectRepository
from ..schemas.comments import (
    CommentCreate,
    CommentRead,
    CommentSection,
    CommentUpdate,
)


router = APIRouter(tags=["comments"])


_ALLOWED_SECTIONS: tuple[str, ...] = (
    "Abstract",
    "Introduction",
    "Methodology",
    "Results",
    "Discussion",
    "Conclusion",
    "FrontMatter",
)


async def _session(
    container: Container = Depends(get_container),
) -> AsyncIterator[AsyncSession]:
    async with container.session_factory() as s:
        yield s


def _user_id(user: UserRead = Depends(get_current_user)) -> str:
    # Phase S1 — delegate to the real session-derived user. The legacy
    # static-id flow remains available via ``RMA_DISABLE_AUTH=1``.
    return user.id


@router.get(
    "/projects/{project_id}/comments",
    response_model=list[CommentRead],
)
async def list_comments(
    project_id: str,
    section: str | None = Query(default=None),
    resolved: bool | None = Query(default=None),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> list[CommentRead]:
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if section is not None and section not in _ALLOWED_SECTIONS:
        raise HTTPException(status_code=422, detail="Unknown section_name")
    repo = SqliteCommentRepository(session)
    rows = await repo.list_for_section(
        project_id=project_id,
        user_id=user_id,
        section_name=section,
        resolved=resolved,
    )
    return [CommentRead.model_validate(r) for r in rows]


@router.post(
    "/projects/{project_id}/comments",
    response_model=CommentRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_comment(
    project_id: str,
    body: CommentCreate,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> CommentRead:
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if body.anchor_end < body.anchor_start:
        raise HTTPException(
            status_code=422,
            detail="anchor_end must be >= anchor_start",
        )
    repo = SqliteCommentRepository(session)
    row = await repo.create(
        project_id=project_id,
        user_id=user_id,
        section_name=body.section_name,
        anchor_start=body.anchor_start,
        anchor_end=body.anchor_end,
        body=body.body,
    )
    return CommentRead.model_validate(row)


@router.patch(
    "/projects/{project_id}/comments/{comment_id}",
    response_model=CommentRead,
)
async def update_comment(
    project_id: str,
    comment_id: str,
    body: CommentUpdate,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> CommentRead:
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    repo = SqliteCommentRepository(session)
    existing = await repo.get(comment_id, user_id)
    if existing is None or existing.project_id != project_id:
        raise HTTPException(status_code=404, detail="Comment not found")
    patch = body.model_dump(exclude_unset=True)
    updated = await repo.update(
        comment_id,
        user_id,
        body=patch.get("body"),
        resolved=patch.get("resolved"),
    )
    assert updated is not None
    return CommentRead.model_validate(updated)


@router.delete(
    "/projects/{project_id}/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_comment(
    project_id: str,
    comment_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> None:
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    repo = SqliteCommentRepository(session)
    existing = await repo.get(comment_id, user_id)
    if existing is None or existing.project_id != project_id:
        raise HTTPException(status_code=404, detail="Comment not found")
    await repo.delete(comment_id, user_id)
    return None
