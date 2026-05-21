"""Phase S1 — per-project member + invitation management.

Endpoints (all under ``/api/projects/{project_id}``):

* ``GET    /members``                  — any member
* ``PATCH  /members/{user_id}``        — owner only
* ``DELETE /members/{user_id}``        — owner only (last-owner protection)
* ``GET    /invitations``              — owner only
* ``POST   /invitations``              — owner only (returns invite URL + raw token)
* ``DELETE /invitations/{invitation_id}`` — owner only
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import delete as sa_delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth_deps import get_current_user
from ..container import Container, get_container
from ..db.models import Invitation, User, new_id
from ..repositories.project_members import ProjectMemberRepository
from ..schemas.auth import (
    InvitationCreate,
    InvitationCreateResponse,
    InvitationRead,
    MemberRead,
    MemberUpdate,
    UserRead,
)
from ..services.auth import audit
from ..services.auth.rbac import require_member, require_role
from ..services.auth.tokens import generate_token, hash_token

router = APIRouter(prefix="/projects/{project_id}", tags=["members"])


INVITATION_TTL = timedelta(days=14)


async def _session_dep(
    container: Container = Depends(get_container),
) -> AsyncIterator[AsyncSession]:
    async with container.session_factory() as s:
        yield s


@router.get("/members", response_model=list[MemberRead])
async def list_members(
    project_id: str,
    user: UserRead = Depends(get_current_user),
    session: AsyncSession = Depends(_session_dep),
) -> list[MemberRead]:
    await require_member(session, project_id=project_id, user_id=user.id)
    repo = ProjectMemberRepository(session)
    return await repo.list_for_project(project_id)


@router.patch("/members/{target_user_id}", response_model=MemberRead)
async def update_member_role(
    project_id: str,
    target_user_id: str,
    body: MemberUpdate,
    user: UserRead = Depends(get_current_user),
    session: AsyncSession = Depends(_session_dep),
) -> MemberRead:
    await require_role(
        session, project_id=project_id, user_id=user.id, required="owner"
    )
    repo = ProjectMemberRepository(session)
    target_role = await repo.get_role(project_id, target_user_id)
    if target_role is None:
        raise HTTPException(status_code=404, detail="Member not found")
    # Last-owner protection — don't let the only owner demote themselves.
    if (
        target_user_id == user.id
        and target_role == "owner"
        and body.role != "owner"
        and (await repo.count_owners(project_id)) <= 1
    ):
        raise HTTPException(
            status_code=409,
            detail="Cannot demote the only owner of the project",
        )
    row = await repo.update_role(
        project_id=project_id, user_id=target_user_id, new_role=body.role
    )
    if row is None:  # pragma: no cover
        raise HTTPException(status_code=404, detail="Member not found")
    await audit.record(
        session,
        user_id=user.id,
        action=audit.ACTION_MEMBER_ROLE_CHANGE,
        payload={"project_id": project_id, "user_id": target_user_id, "new_role": body.role},
    )
    # Re-read so we get the User join.
    members = await repo.list_for_project(project_id)
    for m in members:
        if m.user_id == target_user_id:
            return m
    raise HTTPException(status_code=404, detail="Member not found")  # pragma: no cover


@router.delete("/members/{target_user_id}", status_code=204)
async def remove_member(
    project_id: str,
    target_user_id: str,
    user: UserRead = Depends(get_current_user),
    session: AsyncSession = Depends(_session_dep),
) -> None:
    await require_role(
        session, project_id=project_id, user_id=user.id, required="owner"
    )
    repo = ProjectMemberRepository(session)
    target_role = await repo.get_role(project_id, target_user_id)
    if target_role is None:
        raise HTTPException(status_code=404, detail="Member not found")
    if (
        target_role == "owner"
        and (await repo.count_owners(project_id)) <= 1
    ):
        raise HTTPException(
            status_code=409,
            detail="Cannot remove the only owner of the project",
        )
    await repo.remove(project_id=project_id, user_id=target_user_id)
    await audit.record(
        session,
        user_id=user.id,
        action=audit.ACTION_MEMBER_REMOVE,
        payload={"project_id": project_id, "user_id": target_user_id},
    )
    return None


# ── Invitations ────────────────────────────────────────────────────────


@router.get("/invitations", response_model=list[InvitationRead])
async def list_invitations(
    project_id: str,
    user: UserRead = Depends(get_current_user),
    session: AsyncSession = Depends(_session_dep),
) -> list[InvitationRead]:
    await require_role(
        session, project_id=project_id, user_id=user.id, required="owner"
    )
    rows = (
        await session.execute(
            select(Invitation)
            .where(Invitation.project_id == project_id)
            .order_by(Invitation.created_at.desc())
        )
    ).scalars().all()
    return [InvitationRead.model_validate(r) for r in rows]


@router.post(
    "/invitations",
    response_model=InvitationCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_invitation(
    project_id: str,
    body: InvitationCreate,
    request: Request,
    user: UserRead = Depends(get_current_user),
    session: AsyncSession = Depends(_session_dep),
) -> InvitationCreateResponse:
    await require_role(
        session, project_id=project_id, user_id=user.id, required="owner"
    )
    email = body.email.lower().strip()
    # If a user with this email is already a member, refuse early.
    existing_user = (
        await session.execute(select(User).where(User.email == email))
    ).scalar_one_or_none()
    if existing_user is not None:
        repo = ProjectMemberRepository(session)
        if await repo.is_member(project_id, existing_user.id):
            raise HTTPException(
                status_code=409, detail="User is already a member of this project"
            )

    raw = generate_token()
    inv = Invitation(
        id=new_id(),
        email=email,
        project_id=project_id,
        role=body.role,
        token_hash=hash_token(raw),
        invited_by=user.id,
        expires_at=datetime.now(timezone.utc) + INVITATION_TTL,
    )
    session.add(inv)
    await session.commit()
    await session.refresh(inv)
    await audit.record(
        session,
        user_id=user.id,
        action=audit.ACTION_INVITATION_CREATE,
        payload={"project_id": project_id, "email": email, "role": body.role},
    )

    # Build a self-relative URL. The client is the source of truth for
    # what host to use (Electron, browser tab, tailnet — all differ), so
    # we hand back the path and the client prefixes its own origin.
    base = str(request.base_url).rstrip("/")
    invite_url = f"{base}/invite/{raw}"
    return InvitationCreateResponse(
        invitation=InvitationRead.model_validate(inv),
        invite_url=invite_url,
        token=raw,
    )


@router.delete("/invitations/{invitation_id}", status_code=204)
async def revoke_invitation(
    project_id: str,
    invitation_id: str,
    user: UserRead = Depends(get_current_user),
    session: AsyncSession = Depends(_session_dep),
) -> None:
    await require_role(
        session, project_id=project_id, user_id=user.id, required="owner"
    )
    result = await session.execute(
        sa_delete(Invitation).where(
            Invitation.id == invitation_id,
            Invitation.project_id == project_id,
        )
    )
    await session.commit()
    if (result.rowcount or 0) == 0:
        raise HTTPException(status_code=404, detail="Invitation not found")
    await audit.record(
        session,
        user_id=user.id,
        action=audit.ACTION_INVITATION_REVOKE,
        payload={"project_id": project_id, "invitation_id": invitation_id},
    )
    return None
