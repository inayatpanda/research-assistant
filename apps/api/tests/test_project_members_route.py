"""Phase S1 — project_members routes (members + invitations)."""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _enable_real_auth(monkeypatch):
    monkeypatch.setenv("RMA_DISABLE_AUTH", "0")
    from research_api.services.auth.rate_limit import LOGIN_LIMITER, SIGNUP_LIMITER

    LOGIN_LIMITER.reset()
    SIGNUP_LIMITER.reset()


async def _signup(client, email, password="abcd123456"):
    r = await client.post(
        "/api/auth/signup",
        json={"email": email, "password": password, "display_name": email.split("@")[0]},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _login(client, email, password="abcd123456"):
    r = await client.post(
        "/api/auth/login", json={"email": email, "password": password}
    )
    assert r.status_code == 200, r.text


async def _create_project(client, title="P"):
    r = await client.post(
        "/api/projects", json={"title": title, "study_type": "Systematic Review"}
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _new_user_session(client, email):
    # Sign out current, sign up new — simplest way to switch cookies in
    # this client.
    await client.post("/api/auth/logout")
    return await _signup(client, email)


@pytest.mark.asyncio
async def test_owner_appears_in_member_list_after_create(client):
    await _signup(client, "owner@x.com")
    pid = await _create_project(client)
    r = await client.get(f"/api/projects/{pid}/members")
    assert r.status_code == 200
    members = r.json()
    assert len(members) == 1
    assert members[0]["role"] == "owner"


@pytest.mark.asyncio
async def test_non_member_sees_project_as_404(client):
    await _signup(client, "ownera@x.com")
    pid = await _create_project(client)
    # Switch to a different user.
    await _new_user_session(client, "stranger@x.com")
    r = await client.get(f"/api/projects/{pid}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_invitation_create_and_accept_flow(client):
    owner_id = await _signup(client, "ownerb@x.com")
    pid = await _create_project(client, "Shared project")

    # Owner creates invitation.
    r = await client.post(
        f"/api/projects/{pid}/invitations",
        json={"email": "guest@x.com", "role": "editor"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    token = body["token"]
    assert body["invitation"]["role"] == "editor"
    assert "/invite/" in body["invite_url"]

    # Guest signs up (separately).
    guest_id = await _new_user_session(client, "guest@x.com")
    assert guest_id != owner_id

    # Guest hits the landing endpoint to see what they're accepting.
    r = await client.get(f"/api/auth/invitations/{token}")
    assert r.status_code == 200
    assert r.json()["project_title"] == "Shared project"

    # Guest accepts.
    r = await client.post(f"/api/auth/accept-invitation/{token}")
    assert r.status_code == 200

    # Now the guest can read the project.
    r = await client.get(f"/api/projects/{pid}")
    assert r.status_code == 200

    # Second accept fails (410 — already accepted).
    r = await client.post(f"/api/auth/accept-invitation/{token}")
    assert r.status_code == 410


@pytest.mark.asyncio
async def test_role_change_owner_only(client):
    await _signup(client, "ownerc@x.com")
    pid = await _create_project(client)
    r = await client.post(
        f"/api/projects/{pid}/invitations",
        json={"email": "viewer@x.com", "role": "viewer"},
    )
    token = r.json()["token"]
    viewer_id = await _new_user_session(client, "viewer@x.com")
    await client.post(f"/api/auth/accept-invitation/{token}")

    # Viewer tries to change someone's role — 403 (member but not owner).
    r = await client.patch(
        f"/api/projects/{pid}/members/{viewer_id}", json={"role": "editor"}
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_last_owner_cannot_be_demoted(client):
    owner_id = await _signup(client, "soloowner@x.com")
    pid = await _create_project(client)
    r = await client.patch(
        f"/api/projects/{pid}/members/{owner_id}", json={"role": "editor"}
    )
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_revoke_invitation(client):
    await _signup(client, "ownerd@x.com")
    pid = await _create_project(client)
    r = await client.post(
        f"/api/projects/{pid}/invitations",
        json={"email": "x@x.com", "role": "viewer"},
    )
    inv_id = r.json()["invitation"]["id"]
    r = await client.delete(f"/api/projects/{pid}/invitations/{inv_id}")
    assert r.status_code == 204
    r = await client.delete(f"/api/projects/{pid}/invitations/{inv_id}")
    assert r.status_code == 404
