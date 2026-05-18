"""Phase 8.7 security regression: prove every figures + CONSORT + template
endpoint is scoped by both user_id and project_id.

Same approach as the other test_security_*.py files: drive the live ASGI app
twice with a swapped container.settings.local_user_id.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from research_api.container import get_container

FIX = Path(__file__).parent / "fixtures"


def _switch_user(user_id: str) -> None:
    get_container().settings.local_user_id = user_id


async def _make_project(client, title: str = "P", study_type: str = "Outcome Study") -> str:
    r = await client.post(
        "/api/projects", json={"title": title, "study_type": study_type}
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _upload_png(client, pid: str) -> str:
    data = (FIX / "tiny.png").read_bytes()
    r = await client.post(
        f"/api/projects/{pid}/figures",
        files={"file": ("tiny.png", data, "image/png")},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


# ── Figures ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_figures_list_isolated_per_user(client) -> None:
    _switch_user("alice")
    pid = await _make_project(client, "A")
    await _upload_png(client, pid)
    _switch_user("bob")
    # Bob can't see Alice's project at all
    r = await client.get(f"/api/projects/{pid}/figures")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_get_figure_404_for_other_user(client) -> None:
    _switch_user("alice")
    pid = await _make_project(client, "A")
    fid = await _upload_png(client, pid)
    _switch_user("bob")
    r = await client.get(f"/api/figures/{fid}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_upload_figure_404_when_project_owned_by_other_user(client) -> None:
    _switch_user("alice")
    pid = await _make_project(client, "A")
    _switch_user("bob")
    data = (FIX / "tiny.png").read_bytes()
    r = await client.post(
        f"/api/projects/{pid}/figures",
        files={"file": ("tiny.png", data, "image/png")},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_reorder_figures_rejects_when_ids_include_other_users_figure(client) -> None:
    _switch_user("alice")
    pid_a = await _make_project(client, "A")
    fid_a = await _upload_png(client, pid_a)
    _switch_user("bob")
    pid_b = await _make_project(client, "B")
    fid_b = await _upload_png(client, pid_b)
    # Bob attempts to reorder his project but smuggles Alice's figure id in
    r = await client.post(
        f"/api/projects/{pid_b}/figures/reorder",
        json={"ordered_figure_ids": [fid_b, fid_a]},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_delete_figure_404_for_other_user(client) -> None:
    _switch_user("alice")
    pid = await _make_project(client, "A")
    fid = await _upload_png(client, pid)
    _switch_user("bob")
    r = await client.delete(f"/api/figures/{fid}")
    assert r.status_code == 404


# ── CONSORT ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_consort_get_404_for_other_user(client) -> None:
    _switch_user("alice")
    pid = await _make_project(client, "A", study_type="Randomised Controlled Trial")
    _switch_user("bob")
    r = await client.get(f"/api/projects/{pid}/consort")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_consort_patch_404_for_other_user(client) -> None:
    _switch_user("alice")
    pid = await _make_project(client, "A", study_type="Randomised Controlled Trial")
    _switch_user("bob")
    r = await client.patch(f"/api/projects/{pid}/consort", json={"randomised": 100})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_consort_push_404_for_other_user(client) -> None:
    _switch_user("alice")
    pid = await _make_project(client, "A", study_type="Randomised Controlled Trial")
    _switch_user("bob")
    r = await client.post(f"/api/projects/{pid}/consort/push")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_consort_push_422_when_project_not_rct(client) -> None:
    _switch_user("alice")
    pid = await _make_project(client, "A", study_type="Outcome Study")
    r = await client.post(f"/api/projects/{pid}/consort/push")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_patch_project_template_journal_404_for_other_user(client) -> None:
    _switch_user("alice")
    pid = await _make_project(client, "A")
    _switch_user("bob")
    r = await client.patch(f"/api/projects/{pid}", json={"template_journal": "jbjs"})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_journal_templates_list_is_public_per_user_isolation_not_applicable(
    client,
) -> None:
    """The catalogue is public reference data — no per-user scoping needed.

    Documented here so future security regression cleanups don't flag this
    endpoint as a missing isolation case.
    """
    _switch_user("alice")
    a = await client.get("/api/journal-templates")
    _switch_user("bob")
    b = await client.get("/api/journal-templates")
    assert a.status_code == 200 and b.status_code == 200
    assert a.json() == b.json()
