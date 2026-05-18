"""Phase 8.7 — PATCH /figures/{id} caption and alt_text."""
from __future__ import annotations

from pathlib import Path

import pytest

FIX = Path(__file__).parent / "fixtures"


async def _project(client) -> str:
    r = await client.post(
        "/api/projects", json={"title": "P", "study_type": "Outcome Study"}
    )
    return r.json()["id"]


async def _upload(client, pid: str) -> str:
    data = (FIX / "tiny.png").read_bytes()
    r = await client.post(
        f"/api/projects/{pid}/figures",
        files={"file": ("tiny.png", data, "image/png")},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


@pytest.mark.asyncio
async def test_patch_caption(client) -> None:
    pid = await _project(client)
    fid = await _upload(client, pid)
    r = await client.patch(f"/api/figures/{fid}", json={"caption": "My X-ray"})
    assert r.status_code == 200, r.text
    assert r.json()["caption"] == "My X-ray"


@pytest.mark.asyncio
async def test_patch_alt_text_max_500_chars(client) -> None:
    pid = await _project(client)
    fid = await _upload(client, pid)
    bad = "x" * 501
    r = await client.patch(f"/api/figures/{fid}", json={"alt_text": bad})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_patch_alt_text_accepts(client) -> None:
    pid = await _project(client)
    fid = await _upload(client, pid)
    r = await client.patch(f"/api/figures/{fid}", json={"alt_text": "Knee MRI"})
    assert r.status_code == 200
    assert r.json()["alt_text"] == "Knee MRI"


@pytest.mark.asyncio
async def test_patch_404(client) -> None:
    r = await client.patch("/api/figures/nope", json={"caption": "x"})
    assert r.status_code == 404
