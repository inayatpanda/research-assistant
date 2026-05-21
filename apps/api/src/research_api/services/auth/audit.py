"""Phase S1 — light-weight audit log.

Records auth + sharing events to the ``audit_events`` table. Never
raises — auditing failures must not break the underlying request.
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...db.models import AuditEvent, new_id

logger = logging.getLogger(__name__)

# Known action constants (kept as string for forward-compat).
ACTION_SIGNUP = "signup"
ACTION_LOGIN = "login"
ACTION_LOGOUT = "logout"
ACTION_LOGIN_FAILED = "login_failed"
ACTION_PASSWORD_CHANGE = "password_change"
ACTION_INVITATION_CREATE = "invitation_create"
ACTION_INVITATION_ACCEPT = "invitation_accept"
ACTION_INVITATION_REVOKE = "invitation_revoke"
ACTION_MEMBER_ADD = "member_add"
ACTION_MEMBER_REMOVE = "member_remove"
ACTION_MEMBER_ROLE_CHANGE = "member_role_change"
ACTION_LEGACY_CLAIM = "legacy_claim"


async def record(
    session: AsyncSession,
    *,
    user_id: str | None,
    action: str,
    payload: dict[str, Any] | None = None,
) -> None:
    try:
        event = AuditEvent(
            id=new_id(),
            user_id=user_id,
            action=action,
            payload=payload,
        )
        session.add(event)
        await session.commit()
    except Exception:  # pragma: no cover - defence-in-depth
        logger.exception("audit_record failed action=%s user_id=%s", action, user_id)
        try:
            await session.rollback()
        except Exception:
            pass
