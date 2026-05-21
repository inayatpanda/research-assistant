"""Phase S1 — server-side session management.

Sessions live in the ``sessions`` table. Cookie value = the raw token;
DB stores only its SHA-256 hash. ``resolve_session`` validates expiry +
bumps ``last_seen_at`` on every call.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete as sa_delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.models import Session as SessionModel, User, new_id
from .tokens import generate_token, hash_token

SESSION_TTL = timedelta(days=30)
COOKIE_NAME = "rma_session"


@dataclass
class CreatedSession:
    cookie_value: str
    row: SessionModel


async def create_session(
    session: AsyncSession,
    *,
    user_id: str,
    user_agent: str | None,
    ttl: timedelta = SESSION_TTL,
) -> CreatedSession:
    raw = generate_token()
    now = datetime.now(timezone.utc)
    row = SessionModel(
        id=new_id(),
        user_id=user_id,
        token_hash=hash_token(raw),
        created_at=now,
        expires_at=now + ttl,
        last_seen_at=now,
        user_agent=(user_agent or "")[:500] or None,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return CreatedSession(cookie_value=raw, row=row)


async def resolve_session(
    session: AsyncSession, *, cookie_value: str
) -> tuple[SessionModel, User] | None:
    """Resolve a raw cookie value to (session_row, user).

    Returns ``None`` if the cookie is unknown, expired, or the user has
    been deleted. On success, bumps ``last_seen_at``.
    """
    if not cookie_value:
        return None
    token_hash = hash_token(cookie_value)
    row = (
        await session.execute(
            select(SessionModel).where(SessionModel.token_hash == token_hash)
        )
    ).scalar_one_or_none()
    if row is None:
        return None
    now = datetime.now(timezone.utc)
    expires_at = row.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < now:
        # Expired — purge.
        await session.execute(
            sa_delete(SessionModel).where(SessionModel.id == row.id)
        )
        await session.commit()
        return None
    user = (
        await session.execute(select(User).where(User.id == row.user_id))
    ).scalar_one_or_none()
    if user is None:
        await session.execute(
            sa_delete(SessionModel).where(SessionModel.id == row.id)
        )
        await session.commit()
        return None
    row.last_seen_at = now
    await session.commit()
    return row, user


async def revoke_session_by_cookie(
    session: AsyncSession, *, cookie_value: str
) -> bool:
    if not cookie_value:
        return False
    token_hash = hash_token(cookie_value)
    result = await session.execute(
        sa_delete(SessionModel).where(SessionModel.token_hash == token_hash)
    )
    await session.commit()
    return (result.rowcount or 0) > 0


async def revoke_session_by_id(
    session: AsyncSession, *, session_id: str, user_id: str
) -> bool:
    result = await session.execute(
        sa_delete(SessionModel).where(
            SessionModel.id == session_id, SessionModel.user_id == user_id
        )
    )
    await session.commit()
    return (result.rowcount or 0) > 0


async def revoke_all_for_user(
    session: AsyncSession, *, user_id: str, except_session_id: str | None = None
) -> int:
    stmt = sa_delete(SessionModel).where(SessionModel.user_id == user_id)
    if except_session_id:
        stmt = stmt.where(SessionModel.id != except_session_id)
    result = await session.execute(stmt)
    await session.commit()
    return result.rowcount or 0


async def list_for_user(
    session: AsyncSession, *, user_id: str
) -> list[SessionModel]:
    rows = await session.execute(
        select(SessionModel)
        .where(SessionModel.user_id == user_id)
        .order_by(SessionModel.last_seen_at.desc())
    )
    return list(rows.scalars().all())
