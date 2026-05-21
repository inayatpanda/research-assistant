"""Phase S1 — FastAPI auth dependencies.

* ``get_current_user`` — required. 401 if missing/invalid/expired session.
* ``get_current_user_optional`` — returns ``None`` for anonymous requests.

Both honour the ``RMA_DISABLE_AUTH=1`` legacy-mode escape hatch so the
existing 2260-test suite continues to pass: when the env var is set, we
return a synthetic user backed by ``settings.local_user_id``.

The synthetic user row is materialised on first access so foreign keys
against ``users.id`` (e.g. ``project_members.user_id``) resolve.
"""
from __future__ import annotations

import os
from collections.abc import AsyncIterator

from fastapi import Cookie, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .container import Container, get_container
from .db.models import User, new_id
from .schemas.auth import UserRead
from .services.auth.sessions import COOKIE_NAME, resolve_session


def _is_auth_disabled() -> bool:
    """Test/dev escape hatch.

    Read at request time (not import time) so tests can flip the env var
    between cases.
    """
    return os.environ.get("RMA_DISABLE_AUTH", "").strip() in ("1", "true", "True", "yes")


async def _session_dep(
    container: Container = Depends(get_container),
) -> AsyncIterator[AsyncSession]:
    async with container.session_factory() as s:
        yield s


async def _ensure_legacy_user(
    session: AsyncSession, *, user_id: str
) -> User:
    """Materialise the synthetic legacy user row if it doesn't exist."""
    row = (
        await session.execute(select(User).where(User.id == user_id))
    ).scalar_one_or_none()
    if row is not None:
        return row
    row = User(
        id=user_id,
        email=f"{user_id}@research-assistant.local",
        password_hash="",
        display_name="Local user",
        is_admin=False,
    )
    session.add(row)
    try:
        await session.commit()
        await session.refresh(row)
    except Exception:
        # Another concurrent request may have just inserted it.
        await session.rollback()
        row = (
            await session.execute(select(User).where(User.id == user_id))
        ).scalar_one_or_none()
        if row is None:  # pragma: no cover
            raise
    return row


async def get_current_user(
    request: Request,
    container: Container = Depends(get_container),
    session_cookie: str | None = Cookie(default=None, alias=COOKIE_NAME),
) -> UserRead:
    """Resolve the current user or raise 401.

    Cookie name = :data:`COOKIE_NAME` (``rma_session``).
    """
    # Legacy single-user mode (controlled by env var). Tests + CI rely on it.
    if _is_auth_disabled():
        async with container.session_factory() as s:
            row = await _ensure_legacy_user(
                s, user_id=container.settings.local_user_id
            )
            return UserRead.model_validate(row)

    if not session_cookie:
        raise HTTPException(status_code=401, detail="Not authenticated")

    async with container.session_factory() as s:
        resolved = await resolve_session(s, cookie_value=session_cookie)
        if resolved is None:
            raise HTTPException(status_code=401, detail="Session expired")
        _row, user = resolved
        # Reference request for forward-compat (audit tagging, etc.)
        _ = request
        return UserRead.model_validate(user)


async def get_current_user_optional(
    request: Request,
    container: Container = Depends(get_container),
    session_cookie: str | None = Cookie(default=None, alias=COOKIE_NAME),
) -> UserRead | None:
    if _is_auth_disabled():
        async with container.session_factory() as s:
            row = await _ensure_legacy_user(
                s, user_id=container.settings.local_user_id
            )
            return UserRead.model_validate(row)
    if not session_cookie:
        return None
    async with container.session_factory() as s:
        resolved = await resolve_session(s, cookie_value=session_cookie)
        if resolved is None:
            return None
        _row, user = resolved
        _ = request
        return UserRead.model_validate(user)


def current_user_id(user: UserRead = Depends(get_current_user)) -> str:
    """Compact convenience dep — most routes only need the id."""
    return user.id
