"""Abbreviations: per-project list + replace-all (called on manuscript save)."""
from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..container import Container, get_container
from ..repositories.abbreviations import SqliteAbbreviationRepository
from ..repositories.projects import SqliteProjectRepository
from ..schemas.abbreviation import (
    AbbreviationRead,
    AbbreviationsReplace,
)

router = APIRouter(tags=["abbreviations"])


async def _session(
    container: Container = Depends(get_container),
) -> AsyncIterator[AsyncSession]:
    async with container.session_factory() as s:
        yield s


def _user_id(container: Container = Depends(get_container)) -> str:
    return container.settings.local_user_id


@router.get(
    "/projects/{project_id}/abbreviations", response_model=list[AbbreviationRead]
)
async def list_abbreviations(
    project_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> list[AbbreviationRead]:
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    repo = SqliteAbbreviationRepository(session)
    rows = await repo.list_for_project(project_id, user_id)
    return [AbbreviationRead.model_validate(r) for r in rows]


@router.put(
    "/projects/{project_id}/abbreviations", response_model=list[AbbreviationRead]
)
async def replace_abbreviations(
    project_id: str,
    body: AbbreviationsReplace,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> list[AbbreviationRead]:
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    repo = SqliteAbbreviationRepository(session)
    rows = await repo.replace_all(
        project_id=project_id,
        user_id=user_id,
        items=[(i.short_form, i.long_form) for i in body.items],
    )
    return [AbbreviationRead.model_validate(r) for r in rows]


@router.delete(
    "/abbreviations/{abbreviation_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_abbreviation(
    abbreviation_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> None:
    repo = SqliteAbbreviationRepository(session)
    await repo.delete(abbreviation_id, user_id)
    return None
