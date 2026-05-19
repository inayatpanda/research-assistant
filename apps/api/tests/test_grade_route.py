"""Phase 14 (MP14) — GRADE CRUD routes."""
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


def _body(**over):
    base = {
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
    base.update(over)
    return base


@pytest.mark.asyncio
async def test_list_grade_empty(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    r = await client.get(f"/api/projects/{pid}/review/grade")
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_create_grade_derives_certainty_high(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    r = await client.post(f"/api/projects/{pid}/review/grade", json=_body())
    assert r.status_code == 201, r.text
    payload = r.json()
    assert payload["certainty"] == "high"
    assert payload["outcome_label"] == "Mortality"


@pytest.mark.asyncio
async def test_create_grade_derives_certainty_moderate_with_one_serious(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    body = _body(domain_risk_of_bias="serious")
    r = await client.post(f"/api/projects/{pid}/review/grade", json=body)
    assert r.status_code == 201, r.text
    assert r.json()["certainty"] == "moderate"


@pytest.mark.asyncio
async def test_observational_with_large_effect_upgrades_to_moderate(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    body = _body(starting_certainty="low", upgrade_large_effect="present")
    r = await client.post(f"/api/projects/{pid}/review/grade", json=body)
    assert r.status_code == 201, r.text
    assert r.json()["certainty"] == "moderate"


@pytest.mark.asyncio
async def test_upsert_by_outcome_label(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    r1 = await client.post(f"/api/projects/{pid}/review/grade", json=_body())
    assert r1.status_code == 201
    first_id = r1.json()["id"]

    # Same outcome_label → upsert, not duplicate.
    r2 = await client.post(
        f"/api/projects/{pid}/review/grade",
        json=_body(domain_inconsistency="serious"),
    )
    assert r2.status_code == 201
    assert r2.json()["id"] == first_id
    assert r2.json()["certainty"] == "moderate"

    listed = (await client.get(f"/api/projects/{pid}/review/grade")).json()
    assert len(listed) == 1


@pytest.mark.asyncio
async def test_delete_grade(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    r = await client.post(f"/api/projects/{pid}/review/grade", json=_body())
    gid = r.json()["id"]
    r2 = await client.delete(f"/api/projects/{pid}/review/grade/{gid}")
    assert r2.status_code == 204
    listed = (await client.get(f"/api/projects/{pid}/review/grade")).json()
    assert listed == []


@pytest.mark.asyncio
async def test_delete_unknown_returns_404(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    r = await client.delete(
        f"/api/projects/{pid}/review/grade/does-not-exist"
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_create_with_unknown_meta_id_returns_404(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    body = _body(meta_id="ffffffffffffffffffffffffffffffff")
    r = await client.post(f"/api/projects/{pid}/review/grade", json=body)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_list_for_unknown_project_returns_404(client):
    _switch_user("user-a")
    r = await client.get("/api/projects/nope/review/grade")
    assert r.status_code == 404
