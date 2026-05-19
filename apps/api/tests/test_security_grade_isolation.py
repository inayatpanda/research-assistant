"""Phase 14 (MP14) — GRADE + PROSPERO cross-user/project isolation."""
from __future__ import annotations

import pytest

from research_api.container import get_container


def _switch_user(user_id: str) -> None:
    get_container().settings.local_user_id = user_id


async def _make_project(client, title: str = "GP") -> str:
    r = await client.post(
        "/api/projects",
        json={"title": title, "study_type": "Systematic Review"},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _grade_body():
    return {
        "outcome_label": "Mortality",
        "starting_certainty": "high",
        "domain_risk_of_bias": "not_serious",
        "domain_inconsistency": "not_serious",
        "domain_indirectness": "not_serious",
        "domain_imprecision": "not_serious",
        "domain_publication_bias": "not_serious",
        "upgrade_large_effect": "none",
        "upgrade_dose_response": "none",
        "upgrade_confounders_against": "none",
    }


@pytest.mark.asyncio
async def test_grade_list_cannot_see_other_user(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    await client.post(f"/api/projects/{pid}/review/grade", json=_grade_body())

    _switch_user("user-b")
    r = await client.get(f"/api/projects/{pid}/review/grade")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_grade_delete_404_for_other_user(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    gid = (
        await client.post(
            f"/api/projects/{pid}/review/grade", json=_grade_body()
        )
    ).json()["id"]

    _switch_user("user-b")
    r = await client.delete(f"/api/projects/{pid}/review/grade/{gid}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_grade_isolated_per_project(client):
    _switch_user("user-a")
    pid_a = await _make_project(client, "A")
    pid_b = await _make_project(client, "B")
    await client.post(
        f"/api/projects/{pid_a}/review/grade", json=_grade_body()
    )
    rb = await client.get(f"/api/projects/{pid_b}/review/grade")
    assert rb.status_code == 200
    assert rb.json() == []


@pytest.mark.asyncio
async def test_grade_push_404_for_other_user(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    await client.post(f"/api/projects/{pid}/review/grade", json=_grade_body())

    _switch_user("user-b")
    r = await client.post(f"/api/projects/{pid}/review/grade/push")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_prospero_get_404_for_other_user(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    await client.get(f"/api/projects/{pid}/review/prospero")

    _switch_user("user-b")
    r = await client.get(f"/api/projects/{pid}/review/prospero")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_prospero_patch_404_for_other_user(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    await client.get(f"/api/projects/{pid}/review/prospero")

    _switch_user("user-b")
    r = await client.patch(
        f"/api/projects/{pid}/review/prospero",
        json={"fields": {"title": "leak"}},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_prospero_export_404_for_other_user(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    await client.get(f"/api/projects/{pid}/review/prospero")

    _switch_user("user-b")
    r = await client.post(f"/api/projects/{pid}/review/prospero/export")
    assert r.status_code == 404
