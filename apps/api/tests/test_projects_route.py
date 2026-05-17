import pytest


@pytest.mark.asyncio
async def test_create_project(client):
    r = await client.post(
        "/api/projects",
        json={"title": "Hip Outcomes 2026", "study_type": "Outcome Study"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["id"]
    assert body["user_id"] == "local-user"
    assert body["title"] == "Hip Outcomes 2026"
    assert body["citation_style"] == "vancouver"
    assert body["ai_provider"] == "gemini"


@pytest.mark.asyncio
async def test_list_projects(client):
    await client.post(
        "/api/projects", json={"title": "A", "study_type": "Outcome Study"}
    )
    await client.post(
        "/api/projects", json={"title": "B", "study_type": "Systematic Review"}
    )
    r = await client.get("/api/projects")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 2
    assert {p["title"] for p in body} == {"A", "B"}


@pytest.mark.asyncio
async def test_get_project(client):
    created = (
        await client.post(
            "/api/projects",
            json={"title": "Solo", "study_type": "Outcome Study"},
        )
    ).json()
    r = await client.get(f"/api/projects/{created['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == created["id"]


@pytest.mark.asyncio
async def test_get_unknown_project_returns_404(client):
    r = await client.get("/api/projects/nonexistent")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_create_rejects_invalid_study_type(client):
    r = await client.post(
        "/api/projects", json={"title": "Bad", "study_type": "NotARealType"}
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_delete_project(client):
    created = (
        await client.post(
            "/api/projects",
            json={"title": "Del", "study_type": "Outcome Study"},
        )
    ).json()
    r = await client.delete(f"/api/projects/{created['id']}")
    assert r.status_code == 204
    r2 = await client.get(f"/api/projects/{created['id']}")
    assert r2.status_code == 404
