"""Phase S1 — legacy single-user data claim flow."""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _enable_real_auth(monkeypatch):
    monkeypatch.setenv("RMA_DISABLE_AUTH", "0")
    from research_api.services.auth.rate_limit import LOGIN_LIMITER, SIGNUP_LIMITER

    LOGIN_LIMITER.reset()
    SIGNUP_LIMITER.reset()


async def _seed_legacy_user_with_project(client):
    """Synthesise a legacy user row + project row directly via DB."""
    from research_api.container import get_container
    from research_api.db.models import Project, User, new_id
    container = get_container()
    async with container.session_factory() as s:
        legacy = User(
            id="local-user",
            email="local@research-assistant.local",
            password_hash="",
            display_name="Local user",
        )
        s.add(legacy)
        await s.flush()
        # Add two projects + an article so the counts are interesting.
        for title in ("Old project A", "Old project B"):
            s.add(
                Project(
                    id=new_id(),
                    user_id="local-user",
                    title=title,
                    study_type="Outcome Study",
                )
            )
        await s.commit()


@pytest.mark.asyncio
async def test_legacy_data_status_reports_counts(client):
    await _seed_legacy_user_with_project(client)
    # Now sign up a new user.
    await client.post(
        "/api/auth/signup",
        json={"email": "new@x.com", "password": "abcd123456", "display_name": "N"},
    )
    r = await client.get("/api/auth/legacy-data-status")
    assert r.status_code == 200
    body = r.json()
    assert body["has_legacy"] is True
    assert body["project_count"] == 2
    assert body["legacy_user_id"] == "local-user"


@pytest.mark.asyncio
async def test_claim_legacy_data_repoints_rows(client):
    await _seed_legacy_user_with_project(client)
    r = await client.post(
        "/api/auth/signup",
        json={"email": "claim@x.com", "password": "abcd123456", "display_name": "C"},
    )
    new_user_id = r.json()["id"]

    r = await client.post("/api/auth/claim-legacy-data")
    assert r.status_code == 200
    assert r.json()["has_legacy"] is False

    # After claim, the new user should see those projects.
    r = await client.get("/api/projects")
    assert r.status_code == 200
    titles = sorted(p["title"] for p in r.json())
    assert "Old project A" in titles
    assert "Old project B" in titles

    # Status now reports no legacy.
    r = await client.get("/api/auth/legacy-data-status")
    assert r.json()["has_legacy"] is False
    _ = new_user_id
