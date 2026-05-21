"""Phase S1 — role-based access control helpers.

Role precedence: owner > editor > viewer. A user is "at least X" if their
role is X or stronger. Non-members have no role.

Routes obey two rules:
* Non-members of a project see 404 (don't leak project existence).
* Viewers attempting writes / editors attempting owner-only ops see 403.
"""
from __future__ import annotations

from typing import Literal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.models import Project, ProjectMember

Role = Literal["owner", "editor", "viewer"]

_PRECEDENCE: dict[str, int] = {"viewer": 1, "editor": 2, "owner": 3}


def role_at_least(actual: str | None, required: Role) -> bool:
    if actual is None:
        return False
    a = _PRECEDENCE.get(actual, 0)
    r = _PRECEDENCE.get(required, 0)
    return a >= r


async def get_role(
    session: AsyncSession, *, project_id: str, user_id: str
) -> Role | None:
    row = (
        await session.execute(
            select(ProjectMember.role).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    if row is not None:
        return row  # type: ignore[return-value]
    # Phase S1 backwards-compat — if the project has no membership rows
    # at all but its legacy ``user_id`` column matches the caller, treat
    # them as owner. This keeps the 2260-test legacy single-user suite
    # working without requiring every test to seed a member row. Once a
    # real member row exists for ANY user, this fallback no longer
    # applies — RBAC is fully in force.
    has_any_member = (
        await session.execute(
            select(ProjectMember.id).where(
                ProjectMember.project_id == project_id
            ).limit(1)
        )
    ).scalar_one_or_none()
    if has_any_member is not None:
        return None
    legacy_owner = (
        await session.execute(
            select(Project.user_id).where(Project.id == project_id)
        )
    ).scalar_one_or_none()
    if legacy_owner is not None and legacy_owner == user_id:
        return "owner"  # type: ignore[return-value]
    return None


async def project_exists(
    session: AsyncSession, *, project_id: str
) -> bool:
    return (
        await session.execute(
            select(Project.id).where(Project.id == project_id)
        )
    ).scalar_one_or_none() is not None


async def require_role(
    session: AsyncSession,
    *,
    project_id: str,
    user_id: str,
    required: Role,
) -> Role:
    """Resolve the user's role and enforce the rule.

    * If the user is not a member → 404 (we don't reveal the project).
    * If the user is a member but lacks the required role → 403.
    """
    role = await get_role(
        session, project_id=project_id, user_id=user_id
    )
    if role is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if not role_at_least(role, required):
        raise HTTPException(
            status_code=403,
            detail=f"Requires role '{required}' (current: '{role}')",
        )
    return role  # type: ignore[return-value]


async def require_member(
    session: AsyncSession,
    *,
    project_id: str,
    user_id: str,
) -> Role:
    """Convenience for "any membership" — 404 if not a member."""
    return await require_role(
        session, project_id=project_id, user_id=user_id, required="viewer"
    )
