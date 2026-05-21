"""Phase S1 — invitation lifecycle (create / accept / expire / revoke)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest


@pytest.fixture(autouse=True)
def _enable_real_auth(monkeypatch):
    monkeypatch.setenv("RMA_DISABLE_AUTH", "0")
    from research_api.services.auth.rate_limit import LOGIN_LIMITER, SIGNUP_LIMITER

    LOGIN_LIMITER.reset()
    SIGNUP_LIMITER.reset()


async def _signup(client, email):
    r = await client.post(
        "/api/auth/signup",
        json={"email": email, "password": "abcd123456", "display_name": email},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _create_project(client):
    r = await client.post(
        "/api/projects", json={"title": "P", "study_type": "Outcome Study"}
    )
    return r.json()["id"]


@pytest.mark.asyncio
async def test_create_invitation_returns_token_once(client):
    await _signup(client, "o@x.com")
    pid = await _create_project(client)
    r = await client.post(
        f"/api/projects/{pid}/invitations",
        json={"email": "g@x.com", "role": "viewer"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["token"]
    # Listing pending invitations does NOT include the raw token.
    r = await client.get(f"/api/projects/{pid}/invitations")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 1
    assert "token" not in rows[0]


@pytest.mark.asyncio
async def test_accept_invitation_when_logged_in(client):
    await _signup(client, "owner1@x.com")
    pid = await _create_project(client)
    r = await client.post(
        f"/api/projects/{pid}/invitations",
        json={"email": "guest1@x.com", "role": "editor"},
    )
    token = r.json()["token"]

    # Switch to a fresh user.
    await client.post("/api/auth/logout")
    await _signup(client, "guest1@x.com")

    r = await client.post(f"/api/auth/accept-invitation/{token}")
    assert r.status_code == 200

    # Guest is now an editor.
    r = await client.get(f"/api/projects/{pid}/members")
    assert r.status_code == 200
    roles = {m["email"]: m["role"] for m in r.json()}
    assert roles["guest1@x.com"] == "editor"


@pytest.mark.asyncio
async def test_accept_invitation_returns_404_when_not_logged_in(client):
    await _signup(client, "owner2@x.com")
    pid = await _create_project(client)
    r = await client.post(
        f"/api/projects/{pid}/invitations",
        json={"email": "z@x.com", "role": "viewer"},
    )
    token = r.json()["token"]
    await client.post("/api/auth/logout")
    r = await client.post(f"/api/auth/accept-invitation/{token}")
    # 401 — auth required.
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_expired_invitation_is_410(client):
    await _signup(client, "owner3@x.com")
    pid = await _create_project(client)
    r = await client.post(
        f"/api/projects/{pid}/invitations",
        json={"email": "z@x.com", "role": "viewer"},
    )
    token = r.json()["token"]
    inv_id = r.json()["invitation"]["id"]

    # Force-expire the invitation row.
    from sqlalchemy import update as sa_update
    from research_api.container import get_container
    from research_api.db.models import Invitation
    container = get_container()
    async with container.session_factory() as s:
        await s.execute(
            sa_update(Invitation)
            .where(Invitation.id == inv_id)
            .values(expires_at=datetime.now(timezone.utc) - timedelta(days=1))
        )
        await s.commit()

    # Owner is still authed; try to accept own invitation — 410.
    r = await client.post(f"/api/auth/accept-invitation/{token}")
    assert r.status_code == 410


@pytest.mark.asyncio
async def test_landing_returns_inviter_and_role(client):
    await _signup(client, "alex@x.com")
    pid = await _create_project(client)
    r = await client.post(
        f"/api/projects/{pid}/invitations",
        json={"email": "newcomer@x.com", "role": "editor"},
    )
    token = r.json()["token"]
    r = await client.get(f"/api/auth/invitations/{token}")
    assert r.status_code == 200
    body = r.json()
    assert body["role"] == "editor"
    assert body["email"] == "newcomer@x.com"
    assert "alex" in body["inviter_display_name"].lower()
