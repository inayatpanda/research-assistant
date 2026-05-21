"""D3.3 — ``bounding_coords`` JSON column must round-trip both the legacy
text-anchor shape and the new mobile-pdf shape so the schema can grow
without forcing a migration on existing rows.

The legacy shape (``{rects: [...]}``) is what the desktop reader and the
M2 mobile text-mode reader emit. The Phase D3 PDF reader additionally
carries a discriminator (``type='pdf'``), the 1-based pdf.js ``page``
index, and the literal ``text`` so it can re-anchor on text drift.

Both shapes must:
  * be accepted by ``POST /api/articles/{aid}/highlights`` (no 422),
  * be returned verbatim by ``GET .../highlights`` (no key loss), and
  * carry the same shape end-to-end (POST → GET round-trip).
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


@pytest.mark.asyncio
async def test_anchor_text_shape_roundtrips(client):
    """Legacy desktop / M2 mobile text-mode anchor still works."""
    aid = await _make_article(client)
    body = {
        "page_number": 1,
        "selected_text": "anterior approach",
        "colour": "intro",
        "section": "Introduction",
        # No discriminator, no page metadata — what M2 emits today.
        "bounding_coords": {
            "rects": [{"x0": 0.0, "y0": 0.0, "x1": 1.0, "y1": 0.05}]
        },
    }
    created = (
        await client.post(f"/api/articles/{aid}/highlights", json=body)
    ).json()
    assert created["bounding_coords"]["rects"][0]["x1"] == 1.0
    # Round-trip via list — server must not strip the rect.
    listing = (await client.get(f"/api/articles/{aid}/highlights")).json()
    assert listing[0]["bounding_coords"]["rects"][0]["y1"] == 0.05


@pytest.mark.asyncio
async def test_anchor_pdf_shape_roundtrips(client):
    """D3 mobile PDF anchor carries type/page/text without losing data."""
    aid = await _make_article(client)
    body = {
        "page_number": 3,
        "selected_text": "durable five-year outcomes",
        "colour": "results",
        "section": "Results",
        "bounding_coords": {
            "type": "pdf",
            "page": 3,
            "text": "durable five-year outcomes",
            "rects": [
                {"x0": 0.12, "y0": 0.21, "x1": 0.48, "y1": 0.24},
                {"x0": 0.12, "y0": 0.25, "x1": 0.40, "y1": 0.28},
            ],
        },
    }
    r = await client.post(f"/api/articles/{aid}/highlights", json=body)
    assert r.status_code == 201, r.text
    saved = r.json()
    assert saved["bounding_coords"]["type"] == "pdf"
    assert saved["bounding_coords"]["page"] == 3
    assert saved["bounding_coords"]["text"] == "durable five-year outcomes"
    assert len(saved["bounding_coords"]["rects"]) == 2

    listing = (await client.get(f"/api/articles/{aid}/highlights")).json()
    bc = listing[0]["bounding_coords"]
    assert bc["type"] == "pdf"
    assert bc["page"] == 3
    assert bc["rects"][1]["y1"] == 0.28
