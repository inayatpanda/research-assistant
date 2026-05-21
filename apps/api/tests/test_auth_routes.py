"""Phase S1 — auth routes (signup / login / logout / me / change-password).

The shared ``client`` fixture sets ``RMA_DISABLE_AUTH=1`` so the rest of
the suite keeps the legacy single-user behaviour. These tests
explicitly monkeypatch it OFF.
"""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _enable_real_auth(monkeypatch):
    monkeypatch.setenv("RMA_DISABLE_AUTH", "0")
    # Reset rate-limiter buckets so back-to-back test runs start clean.
    from research_api.services.auth.rate_limit import LOGIN_LIMITER, SIGNUP_LIMITER

    LOGIN_LIMITER.reset()
    SIGNUP_LIMITER.reset()


async def _signup(client, *, email="a@b.com", password="abcd123456", display_name="A"):
    r = await client.post(
        "/api/auth/signup",
        json={"email": email, "password": password, "display_name": display_name},
    )
    return r


@pytest.mark.asyncio
async def test_signup_creates_user_and_sets_cookie(client):
    r = await _signup(client)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["email"] == "a@b.com"
    assert body["display_name"] == "A"
    # Cookie must have been set on the response.
    assert "rma_session" in r.headers.get("set-cookie", "")

    # /me round-trip
    me = await client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "a@b.com"


@pytest.mark.asyncio
async def test_signup_rejects_weak_password(client):
    r = await _signup(client, password="short1")
    assert r.status_code == 422

    r = await _signup(client, password="alllettersnodigit")
    assert r.status_code == 422

    r = await _signup(client, password="0123456789")
    assert r.status_code == 201  # 10 digits is fine — has a digit + length OK


@pytest.mark.asyncio
async def test_login_flow(client):
    await _signup(client, email="x@y.com", password="abcd123456")
    # Logout first.
    await client.post("/api/auth/logout")
    me = await client.get("/api/auth/me")
    assert me.status_code == 401

    # Wrong password
    r = await client.post(
        "/api/auth/login", json={"email": "x@y.com", "password": "wrong12345"}
    )
    assert r.status_code == 401

    # Right password
    r = await client.post(
        "/api/auth/login", json={"email": "x@y.com", "password": "abcd123456"}
    )
    assert r.status_code == 200
    me = await client.get("/api/auth/me")
    assert me.status_code == 200


@pytest.mark.asyncio
async def test_me_returns_401_when_anonymous(client):
    r = await client.get("/api/auth/me")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_change_password_revokes_other_sessions(client, monkeypatch):
    # Signup creates session A.
    await _signup(client, email="p@q.com", password="initialpw1234")

    # /me before
    me = await client.get("/api/auth/me")
    assert me.status_code == 200
    user_id = me.json()["id"]

    # Manually create another session for the same user (simulates a 2nd device).
    from research_api.container import get_container
    from research_api.services.auth.sessions import create_session
    container = get_container()
    async with container.session_factory() as s:
        other = await create_session(s, user_id=user_id, user_agent="other-device")
    assert other.row.id

    r = await client.post(
        "/api/auth/change-password",
        json={"old_password": "initialpw1234", "new_password": "freshpw9999"},
    )
    assert r.status_code == 200

    # Current session still valid
    me = await client.get("/api/auth/me")
    assert me.status_code == 200

    # The "other" session was revoked. We assert this via DB count.
    async with container.session_factory() as s:
        from sqlalchemy import select
        from research_api.db.models import Session as SessionModel

        rows = (
            await s.execute(
                select(SessionModel).where(SessionModel.user_id == user_id)
            )
        ).scalars().all()
    assert len(rows) == 1  # only the cookie-bearing one survived


@pytest.mark.asyncio
async def test_change_password_rejects_wrong_old(client):
    await _signup(client, email="z@y.com", password="initialpw1234")
    r = await client.post(
        "/api/auth/change-password",
        json={"old_password": "WRONG_PASS", "new_password": "freshpw9999"},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_signup_rejects_duplicate_email(client):
    await _signup(client, email="dup@x.com", password="abcd123456")
    r = await _signup(client, email="dup@x.com", password="abcd987654", display_name="B")
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_login_rate_limit_kicks_in(client, monkeypatch):
    # 10 attempts allowed per 5 minutes per IP. The 11th must be 429.
    await _signup(client, email="rl@x.com", password="abcd123456")
    await client.post("/api/auth/logout")
    for _ in range(10):
        await client.post(
            "/api/auth/login", json={"email": "rl@x.com", "password": "wrong12345"}
        )
    r = await client.post(
        "/api/auth/login", json={"email": "rl@x.com", "password": "abcd123456"}
    )
    assert r.status_code == 429
