"""Phase S1 — repository for the project_members join table."""
from __future__ import annotations

from sqlalchemy import delete as sa_delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Project, ProjectMember, User, new_id
from ..schemas.auth import MemberRead


class ProjectMemberRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_project(
        self, project_id: str
    ) -> list[MemberRead]:
        stmt = (
            select(ProjectMember, User)
            .join(User, User.id == ProjectMember.user_id)
            .where(ProjectMember.project_id == project_id)
            .order_by(ProjectMember.created_at.asc())
        )
        rows = (await self.session.execute(stmt)).all()
        out: list[MemberRead] = []
        for pm, user in rows:
            out.append(
                MemberRead(
                    user_id=user.id,
                    email=user.email,
                    display_name=user.display_name,
                    role=pm.role,  # type: ignore[arg-type]
                    created_at=pm.created_at,
                )
            )
        return out

    async def get_role(
        self, project_id: str, user_id: str
    ) -> str | None:
        direct = (
            await self.session.execute(
                select(ProjectMember.role).where(
                    ProjectMember.project_id == project_id,
                    ProjectMember.user_id == user_id,
                )
            )
        ).scalar_one_or_none()
        if direct is not None:
            return direct
        # Legacy fallback (mirrors rbac.get_role) — only when no member
        # rows exist at all for this project.
        has_any_member = (
            await self.session.execute(
                select(ProjectMember.id).where(
                    ProjectMember.project_id == project_id
                ).limit(1)
            )
        ).scalar_one_or_none()
        if has_any_member is not None:
            return None
        legacy_owner = (
            await self.session.execute(
                select(Project.user_id).where(Project.id == project_id)
            )
        ).scalar_one_or_none()
        if legacy_owner is not None and legacy_owner == user_id:
            return "owner"
        return None

    async def is_member(
        self, project_id: str, user_id: str
    ) -> bool:
        return (await self.get_role(project_id, user_id)) is not None

    async def add(
        self,
        *,
        project_id: str,
        user_id: str,
        role: str,
        invited_by: str | None,
    ) -> ProjectMember:
        # Upsert-ish: if a row exists, update the role and return.
        existing = (
            await self.session.execute(
                select(ProjectMember).where(
                    ProjectMember.project_id == project_id,
                    ProjectMember.user_id == user_id,
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            existing.role = role
            await self.session.commit()
            await self.session.refresh(existing)
            return existing
        row = ProjectMember(
            id=new_id(),
            project_id=project_id,
            user_id=user_id,
            role=role,
            invited_by=invited_by,
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def update_role(
        self, *, project_id: str, user_id: str, new_role: str
    ) -> ProjectMember | None:
        row = (
            await self.session.execute(
                select(ProjectMember).where(
                    ProjectMember.project_id == project_id,
                    ProjectMember.user_id == user_id,
                )
            )
        ).scalar_one_or_none()
        if row is None:
            return None
        row.role = new_role
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def remove(self, *, project_id: str, user_id: str) -> bool:
        result = await self.session.execute(
            sa_delete(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
            )
        )
        await self.session.commit()
        return (result.rowcount or 0) > 0

    async def count_owners(self, project_id: str) -> int:
        rows = (
            await self.session.execute(
                select(ProjectMember.id).where(
                    ProjectMember.project_id == project_id,
                    ProjectMember.role == "owner",
                )
            )
        ).all()
        return len(rows)

    async def list_project_ids_for_user(self, user_id: str) -> list[str]:
        # Direct memberships.
        ids: set[str] = set()
        rows = (
            await self.session.execute(
                select(ProjectMember.project_id).where(
                    ProjectMember.user_id == user_id
                )
            )
        ).all()
        ids.update(r[0] for r in rows)
        # Legacy projects with no membership rows at all that match
        # ``projects.user_id``. We materialise this as a NOT-EXISTS clause
        # to keep the query cheap.
        legacy_rows = (
            await self.session.execute(
                select(Project.id).where(
                    Project.user_id == user_id,
                    ~select(ProjectMember.id)
                    .where(ProjectMember.project_id == Project.id)
                    .exists(),
                )
            )
        ).all()
        ids.update(r[0] for r in legacy_rows)
        return list(ids)
