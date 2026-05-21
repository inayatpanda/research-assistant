"""D1.1 — PATCH /api/highlights/{id} must accept a ``colour`` change so the
mobile reader from M2 can recolour a highlight after creation.

The schema validates ``colour`` against the same Literal used at create time,
so an invalid value yields 422 instead of corrupting the row.
"""
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
async def test_patch_colour_persists(client):
    aid = await _make_article(client)
    created = (
        await client.post(f"/api/articles/{aid}/highlights", json=_payload())
    ).json()
    assert created["colour"] == "results"

    r = await client.patch(
        f"/api/highlights/{created['id']}", json={"colour": "discussion"}
    )
    assert r.status_code == 200, r.text
    assert r.json()["colour"] == "discussion"

    # Round-trip via list to confirm it's persisted, not just echoed.
    listing = (await client.get(f"/api/articles/{aid}/highlights")).json()
    assert listing[0]["colour"] == "discussion"


@pytest.mark.asyncio
async def test_patch_colour_rejects_invalid(client):
    aid = await _make_article(client)
    created = (
        await client.post(f"/api/articles/{aid}/highlights", json=_payload())
    ).json()
    r = await client.patch(
        f"/api/highlights/{created['id']}", json={"colour": "purple"}
    )
    assert r.status_code == 422, r.text
