"""Phase 8.7 — POST /projects/{pid}/consort/push: replace-by-class to Methodology."""
from __future__ import annotations

import pytest


async def _project(client, study_type: str = "Randomised Controlled Trial") -> str:
    r = await client.post(
        "/api/projects", json={"title": "P", "study_type": study_type}
    )
    return r.json()["id"]


async def _set_data(client, pid: str) -> None:
    await client.patch(
        f"/api/projects/{pid}/consort",
        json={"randomised": 150, "allocated_intervention": 75, "allocated_control": 75},
    )


@pytest.mark.asyncio
async def test_push_consort_appends_figure_to_methodology(client) -> None:
    pid = await _project(client)
    await _set_data(client, pid)
    r = await client.post(f"/api/projects/{pid}/consort/push")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["section_name"] == "Methodology"
    assert 'class="consort-flow"' in body["content"]
    assert "<figure" in body["content"]


@pytest.mark.asyncio
async def test_push_consort_idempotent_replaces_previous(client) -> None:
    pid = await _project(client)
    await _set_data(client, pid)
    await client.post(f"/api/projects/{pid}/consort/push")
    r2 = await client.post(f"/api/projects/{pid}/consort/push")
    assert r2.status_code == 200
    # Exactly one figure block remains
    content = r2.json()["content"]
    assert content.count('class="consort-flow"') == 1


@pytest.mark.asyncio
async def test_push_consort_422_when_not_rct(client) -> None:
    pid = await _project(client, study_type="Outcome Study")
    r = await client.post(f"/api/projects/{pid}/consort/push")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_push_consort_404_for_unknown_project(client) -> None:
    r = await client.post("/api/projects/none/consort/push")
    assert r.status_code == 404
