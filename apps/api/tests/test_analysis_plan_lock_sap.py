"""Phase 17 (MP17) — Analysis plan lock + SAP export route tests."""
from __future__ import annotations

import pytest


async def _project(client) -> str:
    r = await client.post("/api/projects", json={"title": "T", "study_type": "Randomised Controlled Trial"})
    return r.json()["id"]


async def _plan(client, pid: str, steps=None):
    steps = steps or [
        {"type": "test", "args": {"test_key": "independent_t", "alpha": 0.05}},
        {"type": "plot", "args": {"geom": "box"}},
    ]
    r = await client.post(
        f"/api/projects/{pid}/analysis-plans",
        json={"name": "Primary", "description": "x", "steps": steps},
    )
    return r.json()


# ── Lock ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_lock_plan_sets_hash_and_locked_at(client):
    pid = await _project(client)
    p = await _plan(client, pid)
    r = await client.post(f"/api/projects/{pid}/analysis-plans/{p['id']}/lock")
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["integrity_hash"]) == 64
    assert body["locked_at"] is not None

    g = await client.get(f"/api/projects/{pid}/analysis-plans/{p['id']}")
    assert g.json()["is_locked"] is True
    assert g.json()["integrity_hash"] == body["integrity_hash"]


@pytest.mark.asyncio
async def test_lock_idempotent_preserves_first_locked_at(client):
    pid = await _project(client)
    p = await _plan(client, pid)
    first = await client.post(f"/api/projects/{pid}/analysis-plans/{p['id']}/lock")
    second = await client.post(f"/api/projects/{pid}/analysis-plans/{p['id']}/lock")
    assert first.json()["locked_at"] == second.json()["locked_at"]
    assert first.json()["integrity_hash"] == second.json()["integrity_hash"]


@pytest.mark.asyncio
async def test_locked_plan_refuses_patch_without_force(client):
    pid = await _project(client)
    p = await _plan(client, pid)
    await client.post(f"/api/projects/{pid}/analysis-plans/{p['id']}/lock")
    update = await client.patch(
        f"/api/projects/{pid}/analysis-plans/{p['id']}",
        json={"name": "Hacked"},
    )
    assert update.status_code == 409
    assert "locked" in update.json()["detail"].lower()


@pytest.mark.asyncio
async def test_locked_plan_force_unlock_clears_hash(client):
    pid = await _project(client)
    p = await _plan(client, pid)
    await client.post(f"/api/projects/{pid}/analysis-plans/{p['id']}/lock")
    update = await client.patch(
        f"/api/projects/{pid}/analysis-plans/{p['id']}",
        json={"name": "Revised", "force_unlock": True},
    )
    assert update.status_code == 200
    body = update.json()
    assert body["is_locked"] is False
    assert body["integrity_hash"] is None


@pytest.mark.asyncio
async def test_unlocked_plan_can_be_patched_freely(client):
    pid = await _project(client)
    p = await _plan(client, pid)
    update = await client.patch(
        f"/api/projects/{pid}/analysis-plans/{p['id']}",
        json={"name": "Renamed"},
    )
    assert update.status_code == 200
    assert update.json()["name"] == "Renamed"


# ── SAP export ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_sap_export_docx(client):
    pid = await _project(client)
    p = await _plan(client, pid)
    r = await client.get(
        f"/api/projects/{pid}/analysis-plans/{p['id']}/sap?format=docx"
    )
    assert r.status_code == 200, r.text
    assert r.content[:2] == b"PK"
    assert "attachment" in r.headers["content-disposition"]


@pytest.mark.asyncio
async def test_sap_export_pdf(client):
    pid = await _project(client)
    p = await _plan(client, pid)
    r = await client.get(
        f"/api/projects/{pid}/analysis-plans/{p['id']}/sap?format=pdf"
    )
    assert r.status_code == 200, r.text
    assert r.content[:4] == b"%PDF"


@pytest.mark.asyncio
async def test_sap_export_rejects_unknown_format(client):
    pid = await _project(client)
    p = await _plan(client, pid)
    r = await client.get(
        f"/api/projects/{pid}/analysis-plans/{p['id']}/sap?format=rtf"
    )
    # FastAPI should reject the bad query param with 422 (pattern mismatch).
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_sap_export_404_for_unknown_plan(client):
    pid = await _project(client)
    r = await client.get(
        f"/api/projects/{pid}/analysis-plans/nope/sap?format=docx"
    )
    assert r.status_code == 404
