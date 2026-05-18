"""Phase 8.7 — POST /projects/{pid}/figures upload route."""
from __future__ import annotations

from pathlib import Path

import pytest

FIX = Path(__file__).parent / "fixtures"


async def _create_project(client, study_type: str = "Outcome Study") -> str:
    r = await client.post(
        "/api/projects", json={"title": "P", "study_type": study_type}
    )
    return r.json()["id"]


@pytest.mark.asyncio
async def test_upload_png_returns_201_with_figure_number_1(client) -> None:
    pid = await _create_project(client)
    data = (FIX / "tiny.png").read_bytes()
    r = await client.post(
        f"/api/projects/{pid}/figures",
        files={"file": ("tiny.png", data, "image/png")},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["figure_number"] == 1
    assert body["file_type"] == "image/png"
    assert body["width_px"] == 4 and body["height_px"] == 4
    assert body["file_url"]


@pytest.mark.asyncio
async def test_upload_jpeg_returns_201(client) -> None:
    pid = await _create_project(client)
    data = (FIX / "tiny.jpg").read_bytes()
    r = await client.post(
        f"/api/projects/{pid}/figures",
        files={"file": ("tiny.jpg", data, "image/jpeg")},
    )
    assert r.status_code == 201, r.text
    assert r.json()["file_type"] == "image/jpeg"


@pytest.mark.asyncio
async def test_upload_svg_returns_201_with_null_dimensions(client) -> None:
    pid = await _create_project(client)
    data = (FIX / "tiny.svg").read_bytes()
    r = await client.post(
        f"/api/projects/{pid}/figures",
        files={"file": ("tiny.svg", data, "image/svg+xml")},
    )
    assert r.status_code == 201, r.text
    b = r.json()
    assert b["file_type"] == "image/svg+xml"
    assert b["width_px"] is None and b["height_px"] is None


@pytest.mark.asyncio
async def test_upload_pdf_rejects_415(client) -> None:
    pid = await _create_project(client)
    pdf = b"%PDF-1.4\n%not an image\n"
    r = await client.post(
        f"/api/projects/{pid}/figures",
        files={"file": ("doc.pdf", pdf, "application/pdf")},
    )
    assert r.status_code == 415


@pytest.mark.asyncio
async def test_upload_oversize_rejects_413(client) -> None:
    pid = await _create_project(client)
    big = b"\x89PNG\r\n\x1a\n" + (b"\x00" * (10 * 1024 * 1024 + 1))
    r = await client.post(
        f"/api/projects/{pid}/figures",
        files={"file": ("big.png", big, "image/png")},
    )
    assert r.status_code == 413


@pytest.mark.asyncio
async def test_upload_404_on_wrong_project(client) -> None:
    data = (FIX / "tiny.png").read_bytes()
    r = await client.post(
        "/api/projects/nonexistent/figures",
        files={"file": ("tiny.png", data, "image/png")},
    )
    assert r.status_code == 404
