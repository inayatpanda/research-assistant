"""Phase S1 — auth routes.

* ``POST /api/auth/signup``
* ``POST /api/auth/login``
* ``POST /api/auth/logout``
* ``GET  /api/auth/me``
* ``POST /api/auth/change-password``
* ``GET  /api/auth/sessions``
* ``DELETE /api/auth/sessions/{id}``
* ``POST /api/auth/accept-invitation/{token}``
* ``GET  /api/auth/legacy-data-status``
* ``POST /api/auth/claim-legacy-data``

Cookie config: ``rma_session``, HttpOnly, SameSite=Lax, Path=/, 30 days.
Secure=False matches the locked decision of HTTP-only tailnet for v1.
"""
from __future__ import annotations

import re
from collections.abc import AsyncIterator
from datetime import datetime, timezone

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth_deps import get_current_user
from ..container import Container, get_container
from ..db.models import (
    Article,
    Dataset,
    Invitation,
    Project,
    User,
    new_id,
)
from ..repositories.project_members import ProjectMemberRepository
from ..schemas.auth import (
    ChangePasswordRequest,
    InvitationLanding,
    LegacyDataStatus,
    LoginRequest,
    SessionRead,
    SignupRequest,
    UserRead,
)
from ..services.auth import audit
from ..services.auth.passwords import hash_password, verify_password
from ..services.auth.rate_limit import LOGIN_LIMITER, SIGNUP_LIMITER
from ..services.auth.sessions import (
    COOKIE_NAME,
    SESSION_TTL,
    create_session,
    list_for_user,
    resolve_session,
    revoke_all_for_user,
    revoke_session_by_cookie,
    revoke_session_by_id,
)
from ..services.auth.tokens import hash_token

router = APIRouter(prefix="/auth", tags=["auth"])


COOKIE_MAX_AGE = int(SESSION_TTL.total_seconds())
COOKIE_PATH = "/"
COOKIE_SAMESITE = "lax"


async def _session_dep(
    container: Container = Depends(get_container),
) -> AsyncIterator[AsyncSession]:
    async with container.session_factory() as s:
        yield s


def _client_ip(request: Request) -> str:
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _validate_password_strength(password: str) -> None:
    if len(password) < 10:
        raise HTTPException(
            status_code=422,
            detail="Password must be at least 10 characters",
        )
    if not re.search(r"\d", password):
        raise HTTPException(
            status_code=422,
            detail="Password must contain at least one digit",
        )


def _set_session_cookie(response: Response, cookie_value: str) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=cookie_value,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        secure=False,
        samesite=COOKIE_SAMESITE,
        path=COOKIE_PATH,
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=COOKIE_NAME, path=COOKIE_PATH)


@router.post("/signup", response_model=UserRead, status_code=201)
async def signup(
    body: SignupRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(_session_dep),
) -> UserRead:
    if not SIGNUP_LIMITER.check_and_record(_client_ip(request)):
        raise HTTPException(status_code=429, detail="Too many signup attempts")
    _validate_password_strength(body.password)
    email = body.email.lower().strip()

    existing = (
        await session.execute(select(User).where(User.email == email))
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=409, detail="An account with this email already exists"
        )

    user = User(
        id=new_id(),
        email=email,
        password_hash=hash_password(body.password),
        display_name=body.display_name.strip(),
        is_admin=False,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    created = await create_session(
        session,
        user_id=user.id,
        user_agent=request.headers.get("user-agent"),
    )
    _set_session_cookie(response, created.cookie_value)
    await audit.record(
        session,
        user_id=user.id,
        action=audit.ACTION_SIGNUP,
        payload={"email": email},
    )
    return UserRead.model_validate(user)


@router.post("/login", response_model=UserRead)
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(_session_dep),
) -> UserRead:
    if not LOGIN_LIMITER.check_and_record(_client_ip(request)):
        raise HTTPException(status_code=429, detail="Too many login attempts")
    email = body.email.lower().strip()
    user = (
        await session.execute(select(User).where(User.email == email))
    ).scalar_one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        await audit.record(
            session,
            user_id=None,
            action=audit.ACTION_LOGIN_FAILED,
            payload={"email": email},
        )
        raise HTTPException(status_code=401, detail="Invalid email or password")
    created = await create_session(
        session,
        user_id=user.id,
        user_agent=request.headers.get("user-agent"),
    )
    _set_session_cookie(response, created.cookie_value)
    await audit.record(
        session,
        user_id=user.id,
        action=audit.ACTION_LOGIN,
        payload=None,
    )
    return UserRead.model_validate(user)


@router.post("/logout")
async def logout(
    response: Response,
    session: AsyncSession = Depends(_session_dep),
    session_cookie: str | None = Cookie(default=None, alias=COOKIE_NAME),
) -> dict[str, bool]:
    if session_cookie:
        await revoke_session_by_cookie(session, cookie_value=session_cookie)
    _clear_session_cookie(response)
    return {"ok": True}


@router.get("/me", response_model=UserRead)
async def me(user: UserRead = Depends(get_current_user)) -> UserRead:
    return user


@router.post("/change-password", response_model=UserRead)
async def change_password(
    body: ChangePasswordRequest,
    user: UserRead = Depends(get_current_user),
    session: AsyncSession = Depends(_session_dep),
    session_cookie: str | None = Cookie(default=None, alias=COOKIE_NAME),
) -> UserRead:
    _validate_password_strength(body.new_password)
    db_user = (
        await session.execute(select(User).where(User.id == user.id))
    ).scalar_one_or_none()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if not verify_password(body.old_password, db_user.password_hash):
        raise HTTPException(status_code=403, detail="Old password incorrect")
    db_user.password_hash = hash_password(body.new_password)
    await session.commit()
    await session.refresh(db_user)

    # Revoke all OTHER sessions (keep the current one valid so the caller
    # isn't logged out of the device they just typed the new password on).
    current_session_id: str | None = None
    if session_cookie:
        resolved = await resolve_session(session, cookie_value=session_cookie)
        if resolved is not None:
            current_session_id = resolved[0].id
    await revoke_all_for_user(
        session, user_id=user.id, except_session_id=current_session_id
    )
    await audit.record(
        session,
        user_id=user.id,
        action=audit.ACTION_PASSWORD_CHANGE,
        payload=None,
    )
    return UserRead.model_validate(db_user)


@router.get("/sessions", response_model=list[SessionRead])
async def list_sessions(
    user: UserRead = Depends(get_current_user),
    session: AsyncSession = Depends(_session_dep),
) -> list[SessionRead]:
    rows = await list_for_user(session, user_id=user.id)
    return [SessionRead.model_validate(r) for r in rows]


@router.delete("/sessions/{session_id}", status_code=204)
async def revoke_session_route(
    session_id: str,
    user: UserRead = Depends(get_current_user),
    session: AsyncSession = Depends(_session_dep),
) -> None:
    ok = await revoke_session_by_id(
        session, session_id=session_id, user_id=user.id
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Session not found")
    return None


# ── Invitation acceptance ───────────────────────────────────────────────


@router.get("/invitations/{token}", response_model=InvitationLanding)
async def invitation_landing(
    token: str,
    session: AsyncSession = Depends(_session_dep),
) -> InvitationLanding:
    """Public — given a raw token, return the project + inviter info.

    Used by ``/invite/:token`` to render the accept screen.
    """
    inv = (
        await session.execute(
            select(Invitation).where(Invitation.token_hash == hash_token(token))
        )
    ).scalar_one_or_none()
    if inv is None:
        raise HTTPException(status_code=404, detail="Invitation not found")
    now = datetime.now(timezone.utc)
    expires_at = inv.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < now:
        raise HTTPException(status_code=410, detail="Invitation expired")
    if inv.accepted_at is not None:
        raise HTTPException(status_code=410, detail="Invitation already accepted")
    project = (
        await session.execute(select(Project).where(Project.id == inv.project_id))
    ).scalar_one_or_none()
    inviter = (
        await session.execute(select(User).where(User.id == inv.invited_by))
    ).scalar_one_or_none()
    return InvitationLanding(
        project_id=inv.project_id,
        project_title=project.title if project else "(unknown project)",
        role=inv.role,  # type: ignore[arg-type]
        inviter_display_name=inviter.display_name if inviter else "(unknown user)",
        email=inv.email,
    )


@router.post("/accept-invitation/{token}", response_model=UserRead)
async def accept_invitation(
    token: str,
    user: UserRead = Depends(get_current_user),
    session: AsyncSession = Depends(_session_dep),
) -> UserRead:
    inv = (
        await session.execute(
            select(Invitation).where(Invitation.token_hash == hash_token(token))
        )
    ).scalar_one_or_none()
    if inv is None:
        raise HTTPException(status_code=404, detail="Invitation not found")
    now = datetime.now(timezone.utc)
    expires_at = inv.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < now:
        raise HTTPException(status_code=410, detail="Invitation expired")
    if inv.accepted_at is not None:
        raise HTTPException(status_code=410, detail="Invitation already accepted")

    repo = ProjectMemberRepository(session)
    await repo.add(
        project_id=inv.project_id,
        user_id=user.id,
        role=inv.role,
        invited_by=inv.invited_by,
    )
    inv.accepted_at = now
    inv.accepted_by = user.id
    await session.commit()

    await audit.record(
        session,
        user_id=user.id,
        action=audit.ACTION_INVITATION_ACCEPT,
        payload={"project_id": inv.project_id, "role": inv.role},
    )
    return user


# ── Legacy data claim ──────────────────────────────────────────────────


LEGACY_PLACEHOLDER_HASH = ""  # cannot log in directly


async def _find_legacy_user(session: AsyncSession) -> User | None:
    """Return the placeholder user row (password_hash empty)."""
    rows = (
        await session.execute(
            select(User).where(User.password_hash == LEGACY_PLACEHOLDER_HASH)
        )
    ).scalars().all()
    if not rows:
        return None
    # Prefer the canonical local-user id if present; else first.
    for r in rows:
        if r.email.endswith("@research-assistant.local"):
            return r
    return rows[0]


@router.get("/legacy-data-status", response_model=LegacyDataStatus)
async def legacy_data_status(
    user: UserRead = Depends(get_current_user),
    session: AsyncSession = Depends(_session_dep),
) -> LegacyDataStatus:
    legacy = await _find_legacy_user(session)
    if legacy is None or legacy.id == user.id:
        return LegacyDataStatus(has_legacy=False)
    # Count: projects, articles, datasets.
    proj_ids = [
        r[0]
        for r in (
            await session.execute(
                select(Project.id).where(Project.user_id == legacy.id)
            )
        ).all()
    ]
    article_n = len(
        (
            await session.execute(
                select(Article.id).where(Article.user_id == legacy.id)
            )
        ).all()
    )
    dataset_n = len(
        (
            await session.execute(
                select(Dataset.id).where(Dataset.user_id == legacy.id)
            )
        ).all()
    )
    # If nothing actually points at the legacy user any more (e.g. after
    # a claim), report has_legacy=False so the UI stops prompting.
    if not proj_ids and article_n == 0 and dataset_n == 0:
        return LegacyDataStatus(has_legacy=False, legacy_user_id=legacy.id)
    return LegacyDataStatus(
        has_legacy=True,
        legacy_user_id=legacy.id,
        project_count=len(proj_ids),
        article_count=article_n,
        dataset_count=dataset_n,
    )


@router.post("/claim-legacy-data", response_model=LegacyDataStatus)
async def claim_legacy_data(
    user: UserRead = Depends(get_current_user),
    session: AsyncSession = Depends(_session_dep),
) -> LegacyDataStatus:
    legacy = await _find_legacy_user(session)
    if legacy is None:
        return LegacyDataStatus(has_legacy=False)
    if legacy.id == user.id:
        return LegacyDataStatus(has_legacy=False)

    # Walk every mapped ORM table that has a ``user_id`` column and
    # re-point rows from the legacy id → current user id. Driven off
    # ``Base.metadata`` so we don't have to maintain an enumeration.
    from sqlalchemy import text as sa_text

    from ..db.base import Base

    excluded = {"users", "sessions", "audit_events"}
    for table in Base.metadata.sorted_tables:
        if table.name in excluded:
            continue
        if "user_id" not in table.c:
            continue
        await session.execute(
            sa_text(
                f"UPDATE {table.name} SET user_id = :new_id WHERE user_id = :old_id"
            ),
            {"new_id": user.id, "old_id": legacy.id},
        )
    # Invitations have ``invited_by`` and ``accepted_by`` columns too.
    await session.execute(
        sa_text(
            "UPDATE invitations SET invited_by = :new_id WHERE invited_by = :old_id"
        ),
        {"new_id": user.id, "old_id": legacy.id},
    )
    await session.execute(
        sa_text(
            "UPDATE invitations SET accepted_by = :new_id WHERE accepted_by = :old_id"
        ),
        {"new_id": user.id, "old_id": legacy.id},
    )
    await session.execute(
        sa_text(
            "UPDATE project_members SET invited_by = :new_id WHERE invited_by = :old_id"
        ),
        {"new_id": user.id, "old_id": legacy.id},
    )
    await session.commit()

    await audit.record(
        session,
        user_id=user.id,
        action=audit.ACTION_LEGACY_CLAIM,
        payload={"from_legacy_user_id": legacy.id},
    )
    return LegacyDataStatus(
        has_legacy=False,
        legacy_user_id=legacy.id,
    )
