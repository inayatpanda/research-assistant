"""Phase 20 (MP20) — Cross-user / cross-project isolation regression for
the reporting-checklists module. Every endpoint must 404 when invoked by
a user who does not own the run.
"""
from __future__ import annotations

import pytest

from research_api.container import get_container


def _switch(user_id: str) -> None:
    get_container().settings.local_user_id = user_id


async def _make_project(client, title: str) -> str:
    r = await client.post(
        "/api/projects",
        json={"title": title, "study_type": "Randomised Controlled Trial"},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _make_run(client, pid: str, title: str = "v1") -> dict:
    r = await client.post(
        f"/api/projects/{pid}/checklists",
        json={"checklist_key": "CARE", "title": title},
    )
    assert r.status_code == 201, r.text
    return r.json()


# ── Cross-user (user B cannot see / touch user A's resources) ─────────────


@pytest.mark.asyncio
async def test_user_b_cannot_list_user_a_runs(client) -> None:
    _switch("user-a")
    pa = await _make_project(client, "A proj")
    await _make_run(client, pa)
    _switch("user-b")
    r = await client.get(f"/api/projects/{pa}/checklists")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_user_b_cannot_get_user_a_run(client) -> None:
    _switch("user-a")
    pa = await _make_project(client, "A")
    run = await _make_run(client, pa)
    _switch("user-b")
    r = await client.get(f"/api/projects/{pa}/checklists/{run['id']}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_user_b_cannot_create_run_on_user_a_project(client) -> None:
    _switch("user-a")
    pa = await _make_project(client, "A")
    _switch("user-b")
    r = await client.post(
        f"/api/projects/{pa}/checklists",
        json={"checklist_key": "CARE", "title": "intruder"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_user_b_cannot_patch_user_a_run_item(client) -> None:
    _switch("user-a")
    pa = await _make_project(client, "A")
    run = await _make_run(client, pa)
    _switch("user-b")
    r = await client.patch(
        f"/api/projects/{pa}/checklists/{run['id']}/items/1",
        json={"status": "pass"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_user_b_cannot_auto_check_user_a_run(client) -> None:
    _switch("user-a")
    pa = await _make_project(client, "A")
    run = await _make_run(client, pa)
    _switch("user-b")
    r = await client.post(
        f"/api/projects/{pa}/checklists/{run['id']}/auto-check"
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_user_b_cannot_export_user_a_run(client) -> None:
    _switch("user-a")
    pa = await _make_project(client, "A")
    run = await _make_run(client, pa)
    _switch("user-b")
    r = await client.post(
        f"/api/projects/{pa}/checklists/{run['id']}/export?format=pdf"
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_user_b_cannot_delete_user_a_run(client) -> None:
    _switch("user-a")
    pa = await _make_project(client, "A")
    run = await _make_run(client, pa)
    _switch("user-b")
    r = await client.delete(f"/api/projects/{pa}/checklists/{run['id']}")
    assert r.status_code == 404
    # Verify the run still exists.
    _switch("user-a")
    g = await client.get(f"/api/projects/{pa}/checklists/{run['id']}")
    assert g.status_code == 200


# ── Cross-project (same user but wrong project id) ─────────────────────────


@pytest.mark.asyncio
async def test_run_under_wrong_project_id_returns_404(client) -> None:
    _switch("user-a")
    pa = await _make_project(client, "A")
    pb = await _make_project(client, "B")
    run = await _make_run(client, pa)
    # Looking up project A's run via project B should 404.
    r = await client.get(f"/api/projects/{pb}/checklists/{run['id']}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_patch_run_under_wrong_project_id_returns_404(client) -> None:
    _switch("user-a")
    pa = await _make_project(client, "A")
    pb = await _make_project(client, "B")
    run = await _make_run(client, pa)
    r = await client.patch(
        f"/api/projects/{pb}/checklists/{run['id']}/items/1",
        json={"status": "pass"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_export_run_under_wrong_project_id_returns_404(client) -> None:
    _switch("user-a")
    pa = await _make_project(client, "A")
    pb = await _make_project(client, "B")
    run = await _make_run(client, pa)
    r = await client.post(
        f"/api/projects/{pb}/checklists/{run['id']}/export?format=pdf"
    )
    assert r.status_code == 404
