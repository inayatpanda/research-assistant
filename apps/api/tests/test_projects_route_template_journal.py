"""Phase 8.7 — PATCH /api/projects/{pid} template_journal."""
from __future__ import annotations

import pytest


async def _project(client) -> str:
    r = await client.post(
        "/api/projects", json={"title": "P", "study_type": "Outcome Study"}
    )
    return r.json()["id"]


@pytest.mark.asyncio
async def test_patch_project_template_journal_persists(client) -> None:
    pid = await _project(client)
    r = await client.patch(f"/api/projects/{pid}", json={"template_journal": "jbjs"})
    assert r.status_code == 200, r.text
    assert r.json()["template_journal"] == "jbjs"


@pytest.mark.asyncio
async def test_patch_project_template_journal_unknown_key_422(client) -> None:
    pid = await _project(client)
    r = await client.patch(
        f"/api/projects/{pid}", json={"template_journal": "no-such-journal"}
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_patch_project_template_journal_null_clears(client) -> None:
    pid = await _project(client)
    await client.patch(f"/api/projects/{pid}", json={"template_journal": "jbjs"})
    r = await client.patch(f"/api/projects/{pid}", json={"template_journal": None})
    assert r.status_code == 200
    assert r.json()["template_journal"] is None


@pytest.mark.asyncio
async def test_patch_project_404_for_unknown_project(client) -> None:
    r = await client.patch("/api/projects/none", json={"template_journal": "jbjs"})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_get_project_includes_template_journal(client) -> None:
    pid = await _project(client)
    r = await client.get(f"/api/projects/{pid}")
    assert r.status_code == 200
    assert "template_journal" in r.json()
