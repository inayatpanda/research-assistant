"""Phase S1 — session lifecycle tests."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest


@pytest.fixture(autouse=True)
def _enable_real_auth(monkeypatch):
    monkeypatch.setenv("RMA_DISABLE_AUTH", "0")
    from research_api.services.auth.rate_limit import LOGIN_LIMITER, SIGNUP_LIMITER

    LOGIN_LIMITER.reset()
    SIGNUP_LIMITER.reset()


async def _signup(client, email="a@b.com", pw="abcd123456"):
    r = await client.post(
        "/api/auth/signup",
        json={"email": email, "password": pw, "display_name": "X"},
    )
    assert r.status_code == 201, r.text


@pytest.mark.asyncio
async def test_list_sessions_includes_current(client):
    await _signup(client)
    r = await client.get("/api/auth/sessions")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) >= 1


@pytest.mark.asyncio
async def test_revoke_specific_session(client):
    await _signup(client, email="d@e.com")
    me = await client.get("/api/auth/me")
    user_id = me.json()["id"]
    from research_api.container import get_container
    from research_api.services.auth.sessions import create_session
    container = get_container()
    async with container.session_factory() as s:
        other = await create_session(s, user_id=user_id, user_agent="aux")
    # Delete the other session by id.
    r = await client.delete(f"/api/auth/sessions/{other.row.id}")
    assert r.status_code == 204
    # Try deleting it again — 404.
    r = await client.delete(f"/api/auth/sessions/{other.row.id}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_expired_session_returns_401(client):
    await _signup(client, email="ex@p.com")
    me = await client.get("/api/auth/me")
    assert me.status_code == 200
    user_id = me.json()["id"]

    # Force-expire all sessions for this user by reaching into the DB.
    from sqlalchemy import update as sa_update
    from research_api.container import get_container
    from research_api.db.models import Session as SessionModel
    container = get_container()
    async with container.session_factory() as s:
        await s.execute(
            sa_update(SessionModel)
            .where(SessionModel.user_id == user_id)
            .values(expires_at=datetime.now(timezone.utc) - timedelta(days=1))
        )
        await s.commit()

    me = await client.get("/api/auth/me")
    assert me.status_code == 401


@pytest.mark.asyncio
async def test_logout_revokes_session(client):
    await _signup(client, email="lo@p.com")
    assert (await client.get("/api/auth/me")).status_code == 200
    await client.post("/api/auth/logout")
    assert (await client.get("/api/auth/me")).status_code == 401
