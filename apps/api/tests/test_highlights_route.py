"""E2E tests for /api/articles/{id}/highlights and /api/highlights/{id} routes."""
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


async def _make_article(client) -> str:
    proj = (
        await client.post(
            "/api/projects", json={"title": "P", "study_type": "Outcome Study"}
        )
    ).json()
    pdf = (FIXTURES / "sample.pdf").read_bytes()
    upload = await client.post(
        f"/api/projects/{proj['id']}/articles/upload",
        files={"file": ("paper.pdf", pdf, "application/pdf")},
    )
    return upload.json()["article"]["id"]


def _payload(**over) -> dict:
    base = {
        "page_number": 1,
        "selected_text": "anterior approach showed faster ambulation",
        "colour": "results",
        "section": "Results",
        "bounding_coords": {"rects": [{"x0": 0.1, "y0": 0.2, "x1": 0.4, "y1": 0.23}]},
    }
    base.update(over)
    return base


@pytest.mark.asyncio
async def test_create_and_list_highlights(client):
    aid = await _make_article(client)
    r = await client.post(f"/api/articles/{aid}/highlights", json=_payload())
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["colour"] == "results"
    assert body["bounding_coords"] == {
        "rects": [{"x0": 0.1, "y0": 0.2, "x1": 0.4, "y1": 0.23}]
    }
    listing = await client.get(f"/api/articles/{aid}/highlights")
    assert listing.status_code == 200
    assert len(listing.json()) == 1


@pytest.mark.asyncio
async def test_create_rejects_invalid_colour(client):
    aid = await _make_article(client)
    r = await client.post(f"/api/articles/{aid}/highlights", json=_payload(colour="purple"))
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_create_rejects_out_of_range_coords(client):
    aid = await _make_article(client)
    r = await client.post(
        f"/api/articles/{aid}/highlights",
        json=_payload(bounding_coords={"rects": [{"x0": -0.1, "y0": 0, "x1": 0.5, "y1": 0.1}]}),
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_create_rejects_unknown_article(client):
    r = await client.post("/api/articles/nonexistent/highlights", json=_payload())
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_list_filter_by_colour_and_page(client):
    aid = await _make_article(client)
    await client.post(f"/api/articles/{aid}/highlights", json=_payload(colour="results", page_number=1))
    await client.post(
        f"/api/articles/{aid}/highlights",
        json=_payload(colour="intro", section="Introduction", page_number=1),
    )
    await client.post(f"/api/articles/{aid}/highlights", json=_payload(colour="results", page_number=2))

    only_results = (await client.get(f"/api/articles/{aid}/highlights?colour=results")).json()
    assert len(only_results) == 2

    only_page_1 = (await client.get(f"/api/articles/{aid}/highlights?page=1")).json()
    assert len(only_page_1) == 2


@pytest.mark.asyncio
async def test_update_user_note(client):
    aid = await _make_article(client)
    created = (await client.post(f"/api/articles/{aid}/highlights", json=_payload())).json()
    r = await client.patch(
        f"/api/highlights/{created['id']}", json={"user_note": "my paraphrase"}
    )
    assert r.status_code == 200
    assert r.json()["user_note"] == "my paraphrase"


@pytest.mark.asyncio
async def test_delete(client):
    aid = await _make_article(client)
    created = (await client.post(f"/api/articles/{aid}/highlights", json=_payload())).json()
    r = await client.delete(f"/api/highlights/{created['id']}")
    assert r.status_code == 204
    listing = (await client.get(f"/api/articles/{aid}/highlights")).json()
    assert len(listing) == 0


@pytest.mark.asyncio
async def test_summarise_calls_ai_and_stores_result(client):
    aid = await _make_article(client)
    created = (await client.post(f"/api/articles/{aid}/highlights", json=_payload())).json()
    r = await client.post(f"/api/highlights/{created['id']}/summarise")
    assert r.status_code == 200
    # FakeAIProvider.summarise returns "Summary of: <prefix>"
    assert "Summary of:" in r.json()["ai_summary"]
