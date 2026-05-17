"""E2E tests for /api/articles/{id}/notes."""
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


async def _make_article(client) -> str:
    proj = (
        await client.post("/api/projects", json={"title": "P", "study_type": "Outcome Study"})
    ).json()
    pdf = (FIXTURES / "sample.pdf").read_bytes()
    upload = await client.post(
        f"/api/projects/{proj['id']}/articles/upload",
        files={"file": ("paper.pdf", pdf, "application/pdf")},
    )
    return upload.json()["article"]["id"]


@pytest.mark.asyncio
async def test_get_returns_empty_when_no_note(client):
    aid = await _make_article(client)
    r = await client.get(f"/api/articles/{aid}/notes")
    assert r.status_code == 200
    body = r.json()
    assert body["content"] == ""
    assert body["id"] is None


@pytest.mark.asyncio
async def test_put_then_get_roundtrip(client):
    aid = await _make_article(client)
    put = await client.put(
        f"/api/articles/{aid}/notes", json={"content": "remember to check the cohort definition"}
    )
    assert put.status_code == 200
    assert put.json()["content"] == "remember to check the cohort definition"
    assert put.json()["id"] is not None

    get = await client.get(f"/api/articles/{aid}/notes")
    assert get.json()["content"] == "remember to check the cohort definition"


@pytest.mark.asyncio
async def test_put_updates_existing_note(client):
    aid = await _make_article(client)
    await client.put(f"/api/articles/{aid}/notes", json={"content": "first"})
    second = await client.put(f"/api/articles/{aid}/notes", json={"content": "second"})
    assert second.json()["content"] == "second"
    # Confirm there's still exactly one note row (no duplicate via GET)
    get = await client.get(f"/api/articles/{aid}/notes")
    assert get.json()["content"] == "second"


@pytest.mark.asyncio
async def test_note_for_missing_article_404s(client):
    r = await client.get("/api/articles/nonexistent/notes")
    assert r.status_code == 404
