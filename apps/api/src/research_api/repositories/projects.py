from typing import Protocol

from sqlalchemy import delete as sa_delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Project, new_id
from ..schemas.project import ProjectCreate, ProjectUpdate


class ProjectRepository(Protocol):
    async def create(self, data: ProjectCreate, user_id: str) -> Project: ...
    async def get(self, project_id: str, user_id: str) -> Project | None: ...
    async def list_for_user(self, user_id: str) -> list[Project]: ...
    async def update(
        self, project_id: str, patch: ProjectUpdate, user_id: str
    ) -> Project | None: ...
    async def delete(self, project_id: str, user_id: str) -> None: ...


class SqliteProjectRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, data: ProjectCreate, user_id: str) -> Project:
        project = Project(id=new_id(), user_id=user_id, **data.model_dump())
        self.session.add(project)
        await self.session.commit()
        await self.session.refresh(project)
        return project

    async def get(self, project_id: str, user_id: str) -> Project | None:
        stmt = select(Project).where(
            Project.id == project_id, Project.user_id == user_id
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_for_user(self, user_id: str) -> list[Project]:
        stmt = (
            select(Project)
            .where(Project.user_id == user_id)
            .order_by(Project.created_at.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def update(
        self, project_id: str, patch: ProjectUpdate, user_id: str
    ) -> Project | None:
        existing = await self.get(project_id, user_id)
        if existing is None:
            return None
        for k, v in patch.model_dump(exclude_unset=True).items():
            setattr(existing, k, v)
        await self.session.commit()
        await self.session.refresh(existing)
        return existing

    async def delete(self, project_id: str, user_id: str) -> None:
        stmt = sa_delete(Project).where(
            Project.id == project_id, Project.user_id == user_id
        )
        await self.session.execute(stmt)
        await self.session.commit()
