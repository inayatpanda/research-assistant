from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..container import Container, get_container
from ..repositories.projects import SqliteProjectRepository
from ..schemas.project import ProjectCreate, ProjectRead, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["projects"])


async def _session(
    container: Container = Depends(get_container),
) -> AsyncIterator[AsyncSession]:
    async with container.session_factory() as s:
        yield s


def _user_id(container: Container = Depends(get_container)) -> str:
    return container.settings.local_user_id


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    data: ProjectCreate,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> ProjectRead:
    repo = SqliteProjectRepository(session)
    return await repo.create(data, user_id)  # type: ignore[return-value]


@router.get("", response_model=list[ProjectRead])
async def list_projects(
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> list[ProjectRead]:
    repo = SqliteProjectRepository(session)
    return await repo.list_for_user(user_id)  # type: ignore[return-value]


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(
    project_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> ProjectRead:
    repo = SqliteProjectRepository(session)
    found = await repo.get(project_id, user_id)
    if found is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return found  # type: ignore[return-value]


@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project(
    project_id: str,
    patch: ProjectUpdate,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> ProjectRead:
    repo = SqliteProjectRepository(session)
    updated = await repo.update(project_id, patch, user_id)
    if updated is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return updated  # type: ignore[return-value]


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> None:
    repo = SqliteProjectRepository(session)
    await repo.delete(project_id, user_id)
    return None
