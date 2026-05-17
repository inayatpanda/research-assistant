import pytest


async def _make_project(client) -> str:
    r = await client.post("/api/projects", json={"title": "P", "study_type": "Outcome Study"})
    return r.json()["id"]


@pytest.mark.asyncio
async def test_get_section_returns_empty_when_no_row(client):
    pid = await _make_project(client)
    r = await client.get(f"/api/projects/{pid}/sections/Results")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] is None
    assert body["content"] == ""
    assert body["word_count"] == 0
    assert body["section_name"] == "Results"


@pytest.mark.asyncio
async def test_put_then_get_roundtrip(client):
    pid = await _make_project(client)
    r = await client.put(
        f"/api/projects/{pid}/sections/Results",
        json={"section_name": "Results", "content": "Anterior approach was faster."},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["id"] is not None
    assert body["content"] == "Anterior approach was faster."
    assert body["word_count"] == 4

    r2 = await client.get(f"/api/projects/{pid}/sections/Results")
    assert r2.json()["content"] == "Anterior approach was faster."


@pytest.mark.asyncio
async def test_put_updates_same_row(client):
    pid = await _make_project(client)
    first = (
        await client.put(
            f"/api/projects/{pid}/sections/Results",
            json={"section_name": "Results", "content": "v1"},
        )
    ).json()
    second = (
        await client.put(
            f"/api/projects/{pid}/sections/Results",
            json={"section_name": "Results", "content": "v2 longer content here"},
        )
    ).json()
    assert second["id"] == first["id"]
    assert second["content"] == "v2 longer content here"
    assert second["word_count"] == 4


@pytest.mark.asyncio
async def test_section_unknown_project_404s(client):
    r = await client.get("/api/projects/nope/sections/Results")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_put_section_mismatch_422(client):
    pid = await _make_project(client)
    r = await client.put(
        f"/api/projects/{pid}/sections/Results",
        json={"section_name": "Introduction", "content": "x"},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_invalid_section_name_422(client):
    pid = await _make_project(client)
    r = await client.get(f"/api/projects/{pid}/sections/NotARealSection")
    assert r.status_code == 422
