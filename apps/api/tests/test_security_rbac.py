"""Phase S1 — role-based access control."""
from __future__ import annotations

import pytest

from research_api.services.auth.rbac import role_at_least


@pytest.fixture(autouse=True)
def _enable_real_auth(monkeypatch):
    monkeypatch.setenv("RMA_DISABLE_AUTH", "0")
    from research_api.services.auth.rate_limit import LOGIN_LIMITER, SIGNUP_LIMITER

    LOGIN_LIMITER.reset()
    SIGNUP_LIMITER.reset()


def test_role_precedence():
    # owner > editor > viewer
    assert role_at_least("owner", "owner")
    assert role_at_least("owner", "editor")
    assert role_at_least("owner", "viewer")
    assert role_at_least("editor", "viewer")
    assert role_at_least("editor", "editor")
    assert not role_at_least("editor", "owner")
    assert not role_at_least("viewer", "editor")
    assert not role_at_least(None, "viewer")


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


async def _switch_to_new_user(client, email):
    await client.post("/api/auth/logout")
    return await _signup(client, email)


async def _invite_and_accept(client, owner_email, pid, guest_email, role):
    # Owner currently active.
    r = await client.post(
        f"/api/projects/{pid}/invitations",
        json={"email": guest_email, "role": role},
    )
    token = r.json()["token"]
    await _switch_to_new_user(client, guest_email)
    await client.post(f"/api/auth/accept-invitation/{token}")


@pytest.mark.asyncio
async def test_viewer_cannot_update_project(client):
    await _signup(client, "owner-rbac@x.com")
    pid = await _create_project(client)
    await _invite_and_accept(
        client, "owner-rbac@x.com", pid, "viewer-rbac@x.com", "viewer"
    )
    # Viewer tries to PATCH the project — 403.
    r = await client.patch(
        f"/api/projects/{pid}", json={"title": "Hacked title"}
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_editor_cannot_delete_project(client):
    await _signup(client, "owner-d@x.com")
    pid = await _create_project(client)
    await _invite_and_accept(
        client, "owner-d@x.com", pid, "editor-d@x.com", "editor"
    )
    # Editor tries to DELETE — 403.
    r = await client.delete(f"/api/projects/{pid}")
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_editor_can_update_but_not_manage_members(client):
    await _signup(client, "owner-e@x.com")
    pid = await _create_project(client)
    await _invite_and_accept(
        client, "owner-e@x.com", pid, "editor-e@x.com", "editor"
    )
    # Editor can PATCH project.
    r = await client.patch(
        f"/api/projects/{pid}", json={"title": "Edited"}
    )
    assert r.status_code == 200, r.text
    # Editor cannot create invitations.
    r = await client.post(
        f"/api/projects/{pid}/invitations",
        json={"email": "noone@x.com", "role": "viewer"},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_non_member_writes_get_404(client):
    await _signup(client, "owner-n@x.com")
    pid = await _create_project(client)
    # Switch to stranger.
    await _switch_to_new_user(client, "stranger@x.com")
    # PATCH should be 404 not 403 (no membership row → don't leak existence).
    r = await client.patch(
        f"/api/projects/{pid}", json={"title": "x"}
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_viewer_can_read_project(client):
    await _signup(client, "owner-r@x.com")
    pid = await _create_project(client)
    await _invite_and_accept(
        client, "owner-r@x.com", pid, "viewer-r@x.com", "viewer"
    )
    r = await client.get(f"/api/projects/{pid}")
    assert r.status_code == 200
