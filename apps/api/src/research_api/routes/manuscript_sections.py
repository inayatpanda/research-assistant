"""ManuscriptSection routes — GET (synthesizes empty) + PUT upsert.

Each manuscript section (Introduction/Methodology/Results/Discussion/Abstract/
Conclusion) is one row per (project, user). Phase 4 stores plain text; Phase 5
will swap to TipTap JSON.
"""
from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..container import Container, get_container
from ..repositories.manuscript_sections import SqliteManuscriptSectionRepository
from ..repositories.projects import SqliteProjectRepository
from ..schemas.manuscript_section import (
    ManuscriptSectionName,
    ManuscriptSectionRead,
    ManuscriptSectionUpsert,
)

router = APIRouter(tags=["manuscript_sections"])


async def _session(
    container: Container = Depends(get_container),
) -> AsyncIterator[AsyncSession]:
    async with container.session_factory() as s:
        yield s


def _user_id(container: Container = Depends(get_container)) -> str:
    return container.settings.local_user_id


@router.get(
    "/projects/{project_id}/sections/{section_name}",
    response_model=ManuscriptSectionRead,
)
async def get_section(
    project_id: str,
    section_name: ManuscriptSectionName,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> ManuscriptSectionRead:
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    repo = SqliteManuscriptSectionRepository(session)
    row = await repo.get(
        project_id=project_id, section_name=section_name, user_id=user_id
    )
    if row is None:
        return ManuscriptSectionRead(
            id=None,
            user_id=user_id,
            project_id=project_id,
            section_name=section_name,
            content="",
            word_count=0,
            updated_at=None,
        )
    return ManuscriptSectionRead.model_validate(row)


@router.put(
    "/projects/{project_id}/sections/{section_name}",
    response_model=ManuscriptSectionRead,
)
async def upsert_section(
    project_id: str,
    section_name: ManuscriptSectionName,
    body: ManuscriptSectionUpsert,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> ManuscriptSectionRead:
    if body.section_name != section_name:
        raise HTTPException(
            status_code=422,
            detail="section_name in path must match body.section_name",
        )
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    repo = SqliteManuscriptSectionRepository(session)
    row = await repo.upsert(
        project_id=project_id,
        section_name=section_name,
        content=body.content,
        user_id=user_id,
    )
    return ManuscriptSectionRead.model_validate(row)
