from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth_deps import get_current_user
from ..container import Container, get_container
from ..db.models import Project, ProjectMember, new_id
from ..repositories.project_members import ProjectMemberRepository
from ..repositories.projects import SqliteProjectRepository
from ..schemas.auth import UserRead
from ..schemas.project import ProjectCreate, ProjectRead, ProjectUpdate
from ..services.auth.rbac import require_role
from ..services.journal_templates.catalogue import get_template

router = APIRouter(prefix="/projects", tags=["projects"])


async def _session(
    container: Container = Depends(get_container),
) -> AsyncIterator[AsyncSession]:
    async with container.session_factory() as s:
        yield s


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    data: ProjectCreate,
    session: AsyncSession = Depends(_session),
    user: UserRead = Depends(get_current_user),
) -> ProjectRead:
    repo = SqliteProjectRepository(session)
    project = await repo.create(data, user.id)
    # Auto-insert owner membership row so the creator is immediately a member.
    members = ProjectMemberRepository(session)
    await members.add(
        project_id=project.id,
        user_id=user.id,
        role="owner",
        invited_by=None,
    )
    return project  # type: ignore[return-value]


@router.get("", response_model=list[ProjectRead])
async def list_projects(
    session: AsyncSession = Depends(_session),
    user: UserRead = Depends(get_current_user),
) -> list[ProjectRead]:
    # List every project this user is a member of (any role).
    pm_repo = ProjectMemberRepository(session)
    project_ids = await pm_repo.list_project_ids_for_user(user.id)
    if not project_ids:
        return []
    rows = (
        await session.execute(
            select(Project)
            .where(Project.id.in_(project_ids))
            .order_by(Project.created_at.desc())
        )
    ).scalars().all()
    return [ProjectRead.model_validate(r) for r in rows]


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(
    project_id: str,
    session: AsyncSession = Depends(_session),
    user: UserRead = Depends(get_current_user),
) -> ProjectRead:
    pm_repo = ProjectMemberRepository(session)
    if not await pm_repo.is_member(project_id, user.id):
        raise HTTPException(status_code=404, detail="Project not found")
    project = (
        await session.execute(select(Project).where(Project.id == project_id))
    ).scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectRead.model_validate(project)


@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project(
    project_id: str,
    patch: ProjectUpdate,
    session: AsyncSession = Depends(_session),
    user: UserRead = Depends(get_current_user),
) -> ProjectRead:
    # Editors and owners may update; viewers may not.
    await require_role(
        session, project_id=project_id, user_id=user.id, required="editor"
    )
    fields = patch.model_dump(exclude_unset=True)
    if "template_journal" in fields:
        key = fields["template_journal"]
        if key is not None and get_template(key) is None:
            raise HTTPException(
                status_code=422,
                detail=f"Unknown journal template key: {key!r}",
            )
    project = (
        await session.execute(select(Project).where(Project.id == project_id))
    ).scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    for k, v in fields.items():
        setattr(project, k, v)
    await session.commit()
    await session.refresh(project)
    return ProjectRead.model_validate(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    session: AsyncSession = Depends(_session),
    user: UserRead = Depends(get_current_user),
) -> None:
    # Owner-only.
    await require_role(
        session, project_id=project_id, user_id=user.id, required="owner"
    )
    repo = SqliteProjectRepository(session)
    await repo.delete(project_id, project_user_id := (
        # Use whatever projects.user_id currently is — the repository
        # contract still requires it, but RBAC already gated the call.
        (
            await session.execute(
                select(Project.user_id).where(Project.id == project_id)
            )
        ).scalar_one()
    ))
    _ = project_user_id
    return None
