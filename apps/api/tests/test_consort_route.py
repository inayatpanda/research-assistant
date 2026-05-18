"""Phase 8.7 — CONSORT GET / PATCH route."""
from __future__ import annotations

import base64

import pytest


async def _project(client, study_type: str = "Randomised Controlled Trial") -> str:
    r = await client.post(
        "/api/projects", json={"title": "P", "study_type": study_type}
    )
    return r.json()["id"]


@pytest.mark.asyncio
async def test_get_consort_returns_data_and_svg(client) -> None:
    pid = await _project(client)
    r = await client.get(f"/api/projects/{pid}/consort")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "data" in body and "svg_base64" in body and "warnings" in body
    # SVG decodes
    raw = base64.b64decode(body["svg_base64"])
    assert raw.startswith(b"<svg")


@pytest.mark.asyncio
async def test_get_consort_creates_blank_row_when_missing(client) -> None:
    pid = await _project(client)
    r = await client.get(f"/api/projects/{pid}/consort")
    assert r.status_code == 200
    assert r.json()["data"]["randomised"] is None


@pytest.mark.asyncio
async def test_patch_consort_persists_partial_update(client) -> None:
    pid = await _project(client)
    r = await client.patch(
        f"/api/projects/{pid}/consort",
        json={"randomised": 150, "allocated_intervention": 75, "allocated_control": 75},
    )
    assert r.status_code == 200, r.text
    body = r.json()["data"]
    assert body["randomised"] == 150
    assert body["allocated_intervention"] == 75


@pytest.mark.asyncio
async def test_patch_consort_returns_warnings_when_arithmetic_inconsistent(client) -> None:
    pid = await _project(client)
    r = await client.patch(
        f"/api/projects/{pid}/consort",
        json={"randomised": 150, "allocated_intervention": 80, "allocated_control": 80},
    )
    assert r.status_code == 200
    assert any("allocated" in w for w in r.json()["warnings"])


@pytest.mark.asyncio
async def test_consort_404_when_project_missing(client) -> None:
    r = await client.get("/api/projects/none/consort")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_consort_get_works_for_non_rct_project(client) -> None:
    """GET is permissive so the editor can show the form even for non-RCT projects."""
    pid = await _project(client, study_type="Outcome Study")
    r = await client.get(f"/api/projects/{pid}/consort")
    assert r.status_code == 200
