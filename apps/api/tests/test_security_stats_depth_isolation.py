"""Phase 17 (MP17) — Cross-user/project isolation regression for stats depth.

Covers populations, imputation runs, post-hoc, sensitivity, CACE, lock,
SAP export, and instrument binding.
"""
from __future__ import annotations

import pytest

from research_api.container import get_container


CSV_DATA = (
    b"score,arm,assigned,received,age\n"
    + b"10,A,1,1,40\n12,A,1,1,42\n14,A,1,1,38\n11,A,1,0,45\n13,A,1,1,44\n9,A,1,0,41\n"
    + b"6,B,0,0,40\n8,B,0,0,43\n7,B,0,0,39\n8,B,0,1,45\n6,B,0,0,42\n9,B,0,0,40\n"
)


def _switch(user_id: str) -> None:
    get_container().settings.local_user_id = user_id


async def _make_project(client, title: str) -> str:
    r = await client.post("/api/projects", json={"title": title, "study_type": "Randomised Controlled Trial"})
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _upload(client, pid: str) -> dict:
    files = {"file": ("data.csv", CSV_DATA, "text/csv")}
    r = await client.post(f"/api/projects/{pid}/datasets", files=files)
    assert r.status_code == 201, r.text
    return r.json()


async def _population(client, pid: str, did: str) -> dict:
    r = await client.post(
        f"/api/projects/{pid}/datasets/{did}/populations",
        json={
            "name": "ITT",
            "definition": {"filter": "", "label": "ITT"},
            "study_assignment_field": "assigned",
            "treatment_received_field": "received",
        },
    )
    return r.json()


async def _analysis(client, pid: str, did: str) -> dict:
    r = await client.post(
        f"/api/projects/{pid}/datasets/{did}/analyses",
        json={
            "question_type": "group_comparison",
            "chosen_test": "independent_t",
            "variables": {"outcome": "score", "groups": "arm"},
        },
    )
    return r.json()


async def _plan(client, pid: str) -> dict:
    r = await client.post(
        f"/api/projects/{pid}/analysis-plans",
        json={"name": "Plan", "steps": [{"type": "test", "args": {}}]},
    )
    return r.json()


# ── Populations ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_user_b_cannot_list_user_a_populations(client):
    _switch("user-a")
    pa = await _make_project(client, "A")
    ds = await _upload(client, pa)
    await _population(client, pa, ds["id"])

    _switch("user-b")
    r = await client.get(f"/api/projects/{pa}/datasets/{ds['id']}/populations")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_user_b_cannot_read_user_a_population(client):
    _switch("user-a")
    pa = await _make_project(client, "A")
    ds = await _upload(client, pa)
    pop = await _population(client, pa, ds["id"])

    _switch("user-b")
    r = await client.get(
        f"/api/projects/{pa}/datasets/{ds['id']}/populations/{pop['id']}"
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_user_b_cannot_patch_user_a_population(client):
    _switch("user-a")
    pa = await _make_project(client, "A")
    ds = await _upload(client, pa)
    pop = await _population(client, pa, ds["id"])

    _switch("user-b")
    r = await client.patch(
        f"/api/projects/{pa}/datasets/{ds['id']}/populations/{pop['id']}",
        json={"name": "Hacked"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_user_b_cannot_delete_user_a_population(client):
    _switch("user-a")
    pa = await _make_project(client, "A")
    ds = await _upload(client, pa)
    pop = await _population(client, pa, ds["id"])

    _switch("user-b")
    r = await client.delete(
        f"/api/projects/{pa}/datasets/{ds['id']}/populations/{pop['id']}"
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_user_b_cannot_preview_user_a_population(client):
    _switch("user-a")
    pa = await _make_project(client, "A")
    ds = await _upload(client, pa)
    pop = await _population(client, pa, ds["id"])

    _switch("user-b")
    r = await client.post(
        f"/api/projects/{pa}/datasets/{ds['id']}/populations/{pop['id']}/preview"
    )
    assert r.status_code == 404


# ── Imputation ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_user_b_cannot_create_imputation_run_on_user_a_dataset(client):
    _switch("user-a")
    pa = await _make_project(client, "A")
    ds = await _upload(client, pa)

    _switch("user-b")
    r = await client.post(
        f"/api/projects/{pa}/datasets/{ds['id']}/impute",
        json={"method": "mean", "target_cols": ["score"], "n_imputations": 1, "seed": 1},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_user_b_cannot_list_user_a_imputation_runs(client):
    _switch("user-a")
    pa = await _make_project(client, "A")
    ds = await _upload(client, pa)
    await client.post(
        f"/api/projects/{pa}/datasets/{ds['id']}/impute",
        json={"method": "mean", "target_cols": ["score"], "n_imputations": 1, "seed": 1},
    )

    _switch("user-b")
    r = await client.get(
        f"/api/projects/{pa}/datasets/{ds['id']}/imputation-runs"
    )
    assert r.status_code == 404


# ── CACE + sensitivity ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_user_b_cannot_run_cace_on_user_a_analysis(client):
    _switch("user-a")
    pa = await _make_project(client, "A")
    ds = await _upload(client, pa)
    a = await _analysis(client, pa, ds["id"])

    _switch("user-b")
    r = await client.post(
        f"/api/projects/{pa}/analyses/{a['id']}/cace",
        json={"outcome": "score", "assigned": "assigned", "received": "received"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_user_b_cannot_run_sensitivity_on_user_a_analysis(client):
    _switch("user-a")
    pa = await _make_project(client, "A")
    ds = await _upload(client, pa)
    a = await _analysis(client, pa, ds["id"])

    _switch("user-b")
    r = await client.post(
        f"/api/projects/{pa}/analyses/{a['id']}/sensitivity",
        json={"type": "worst_case", "outcome": "score", "group": "arm"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_user_b_cannot_run_post_hoc_on_user_a_analysis(client):
    _switch("user-a")
    pa = await _make_project(client, "A")
    ds = await _upload(client, pa)
    a = await _analysis(client, pa, ds["id"])

    _switch("user-b")
    r = await client.post(
        f"/api/projects/{pa}/analyses/{a['id']}/post-hoc",
        json={"method": "tukey", "outcome": "score", "groups": "arm"},
    )
    assert r.status_code == 404


# ── Lock + SAP ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_user_b_cannot_lock_user_a_plan(client):
    _switch("user-a")
    pa = await _make_project(client, "A")
    p = await _plan(client, pa)

    _switch("user-b")
    r = await client.post(f"/api/projects/{pa}/analysis-plans/{p['id']}/lock")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_user_b_cannot_export_user_a_sap(client):
    _switch("user-a")
    pa = await _make_project(client, "A")
    p = await _plan(client, pa)

    _switch("user-b")
    r = await client.get(
        f"/api/projects/{pa}/analysis-plans/{p['id']}/sap?format=docx"
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_user_b_cannot_force_unlock_user_a_plan(client):
    _switch("user-a")
    pa = await _make_project(client, "A")
    p = await _plan(client, pa)
    await client.post(f"/api/projects/{pa}/analysis-plans/{p['id']}/lock")

    _switch("user-b")
    r = await client.patch(
        f"/api/projects/{pa}/analysis-plans/{p['id']}",
        json={"name": "Hacked", "force_unlock": True},
    )
    assert r.status_code == 404


# ── Instrument binding ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_user_b_cannot_bind_user_a_variable_to_instrument(client):
    _switch("user-a")
    pa = await _make_project(client, "A")
    ds = await _upload(client, pa)
    var_id = ds["variables"][0]["id"]

    _switch("user-b")
    r = await client.patch(
        f"/api/projects/{pa}/datasets/{ds['id']}/variables/{var_id}/instrument-binding",
        json={"instrument_key": "HHS"},
    )
    assert r.status_code == 404


# ── IRR ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_user_b_cannot_call_irr_route_on_user_a_dataset(client):
    _switch("user-a")
    pa = await _make_project(client, "A")
    ds = await _upload(client, pa)

    _switch("user-b")
    r = await client.post(
        f"/api/projects/{pa}/datasets/{ds['id']}/irr",
        json={"method": "fleiss", "matrix": [[5, 0], [5, 0]]},
    )
    assert r.status_code == 404


# ── Cross-project (same user) ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_population_not_visible_under_different_project(client):
    _switch("user-a")
    pa = await _make_project(client, "A")
    pb = await _make_project(client, "B")
    ds = await _upload(client, pa)
    pop = await _population(client, pa, ds["id"])
    # Same user, but project B — should not be able to reach pa's dataset
    r = await client.get(
        f"/api/projects/{pb}/datasets/{ds['id']}/populations/{pop['id']}"
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_analysis_population_route_404_for_missing_population(client):
    _switch("user-a")
    pa = await _make_project(client, "A")
    ds = await _upload(client, pa)
    r = await client.post(
        f"/api/projects/{pa}/datasets/{ds['id']}/populations/missing/preview"
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_user_b_cannot_patch_user_a_plan_when_locked(client):
    _switch("user-a")
    pa = await _make_project(client, "A")
    p = await _plan(client, pa)
    await client.post(f"/api/projects/{pa}/analysis-plans/{p['id']}/lock")

    _switch("user-b")
    r = await client.patch(
        f"/api/projects/{pa}/analysis-plans/{p['id']}",
        json={"name": "Hacked"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_lock_404_for_unknown_plan(client):
    _switch("user-a")
    pa = await _make_project(client, "A")
    r = await client.post(f"/api/projects/{pa}/analysis-plans/missing/lock")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_sap_404_for_unknown_project(client):
    _switch("user-a")
    pa = await _make_project(client, "A")
    p = await _plan(client, pa)
    r = await client.get(
        f"/api/projects/wrong-project/analysis-plans/{p['id']}/sap?format=docx"
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_user_b_cannot_list_user_a_plans(client):
    _switch("user-a")
    pa = await _make_project(client, "A")
    await _plan(client, pa)

    _switch("user-b")
    r = await client.get(f"/api/projects/{pa}/analysis-plans")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_user_b_cannot_create_population_on_user_a_dataset(client):
    _switch("user-a")
    pa = await _make_project(client, "A")
    ds = await _upload(client, pa)

    _switch("user-b")
    r = await client.post(
        f"/api/projects/{pa}/datasets/{ds['id']}/populations",
        json={
            "name": "Steal",
            "definition": {"filter": "", "label": "x"},
            "study_assignment_field": "assigned",
        },
    )
    assert r.status_code == 404
