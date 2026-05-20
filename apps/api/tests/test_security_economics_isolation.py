"""Phase 18 (MP18) — Cross-user / cross-project isolation regression for the
Health Economics module. Every endpoint must 404 when invoked by a user who
does not own the analysis.
"""
from __future__ import annotations

import pytest

from research_api.container import get_container


CSV_DATA = (
    b"patient_id,treatment,cost_total,utility\n"
    + b"p1,anterior,1500,0.85\np2,anterior,1700,0.82\n"
    + b"p3,anterior,1600,0.88\np4,anterior,1800,0.80\n"
    + b"p5,control,1000,0.70\np6,control,1100,0.65\n"
    + b"p7,control,1200,0.72\np8,control,1050,0.68\n"
)


def _switch(user_id: str) -> None:
    get_container().settings.local_user_id = user_id


async def _make_project(client, title: str) -> str:
    r = await client.post(
        "/api/projects",
        json={"title": title, "study_type": "Randomised Controlled Trial"},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _upload(client, pid: str) -> dict:
    files = {"file": ("data.csv", CSV_DATA, "text/csv")}
    r = await client.post(f"/api/projects/{pid}/datasets", files=files)
    assert r.status_code == 201, r.text
    return r.json()


async def _create_economic(client, pid: str, did: str) -> dict:
    body = {
        "name": "CEA",
        "dataset_id": did,
        "treatment_col": "treatment",
        "comparator_label": "control",
        "intervention_label": "anterior",
        "cost_columns": [
            {"col": "cost_total", "role": "cost_total"},
            {"col": "utility", "role": "qaly_weight"},
        ],
        "bootstrap_n": 100,
    }
    r = await client.post(f"/api/projects/{pid}/economic-analyses", json=body)
    assert r.status_code == 201, r.text
    return r.json()


# ─── LIST + GET + PATCH + DELETE ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_user_b_cannot_list_user_a_economic_analyses(client):
    _switch("user-a")
    pa = await _make_project(client, "A")
    ds = await _upload(client, pa)
    await _create_economic(client, pa, ds["id"])

    _switch("user-b")
    r = await client.get(f"/api/projects/{pa}/economic-analyses")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_user_b_cannot_get_user_a_economic_analysis(client):
    _switch("user-a")
    pa = await _make_project(client, "A")
    ds = await _upload(client, pa)
    e = await _create_economic(client, pa, ds["id"])

    _switch("user-b")
    r = await client.get(f"/api/projects/{pa}/economic-analyses/{e['id']}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_user_b_cannot_patch_user_a_economic_analysis(client):
    _switch("user-a")
    pa = await _make_project(client, "A")
    ds = await _upload(client, pa)
    e = await _create_economic(client, pa, ds["id"])

    _switch("user-b")
    r = await client.patch(
        f"/api/projects/{pa}/economic-analyses/{e['id']}",
        json={"name": "Hacked"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_user_b_cannot_delete_user_a_economic_analysis(client):
    _switch("user-a")
    pa = await _make_project(client, "A")
    ds = await _upload(client, pa)
    e = await _create_economic(client, pa, ds["id"])

    _switch("user-b")
    r = await client.delete(
        f"/api/projects/{pa}/economic-analyses/{e['id']}"
    )
    assert r.status_code == 404


# ─── CREATE w/ other user's dataset ───────────────────────────────────────


@pytest.mark.asyncio
async def test_user_b_cannot_create_economic_on_user_a_project(client):
    _switch("user-a")
    pa = await _make_project(client, "A")
    ds = await _upload(client, pa)

    _switch("user-b")
    r = await client.post(
        f"/api/projects/{pa}/economic-analyses",
        json={
            "name": "Hack",
            "dataset_id": ds["id"],
            "treatment_col": "treatment",
            "comparator_label": "control",
            "intervention_label": "anterior",
        },
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_user_b_cannot_create_economic_with_user_a_dataset(client):
    _switch("user-a")
    pa = await _make_project(client, "A")
    ds = await _upload(client, pa)

    _switch("user-b")
    pb = await _make_project(client, "B")
    r = await client.post(
        f"/api/projects/{pb}/economic-analyses",
        json={
            "name": "Hack",
            "dataset_id": ds["id"],  # user-a's dataset
            "treatment_col": "treatment",
            "comparator_label": "control",
            "intervention_label": "anterior",
        },
    )
    assert r.status_code == 404


# ─── RUN / SENSITIVITY / INTERPRET / PUSH ─────────────────────────────────


@pytest.mark.asyncio
async def test_user_b_cannot_run_user_a_economic_analysis(client):
    _switch("user-a")
    pa = await _make_project(client, "A")
    ds = await _upload(client, pa)
    e = await _create_economic(client, pa, ds["id"])

    _switch("user-b")
    r = await client.post(f"/api/projects/{pa}/economic-analyses/{e['id']}/run")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_user_b_cannot_run_sensitivity_on_user_a_economic_analysis(client):
    _switch("user-a")
    pa = await _make_project(client, "A")
    ds = await _upload(client, pa)
    e = await _create_economic(client, pa, ds["id"])

    _switch("user-b")
    r = await client.post(
        f"/api/projects/{pa}/economic-analyses/{e['id']}/sensitivity?type=dsa",
        json={"parameter_ranges": {"mean_cost_diff": {"low": 0, "high": 1}}},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_user_b_cannot_interpret_user_a_economic_analysis(client):
    _switch("user-a")
    pa = await _make_project(client, "A")
    ds = await _upload(client, pa)
    e = await _create_economic(client, pa, ds["id"])

    _switch("user-b")
    r = await client.post(
        f"/api/projects/{pa}/economic-analyses/{e['id']}/interpret"
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_user_b_cannot_push_user_a_economic_analysis(client):
    _switch("user-a")
    pa = await _make_project(client, "A")
    ds = await _upload(client, pa)
    e = await _create_economic(client, pa, ds["id"])

    _switch("user-b")
    r = await client.post(
        f"/api/projects/{pa}/economic-analyses/{e['id']}/push",
        json={"section": "Results"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_user_b_cannot_export_cheers_report_for_user_a_analysis(client):
    _switch("user-a")
    pa = await _make_project(client, "A")
    ds = await _upload(client, pa)
    e = await _create_economic(client, pa, ds["id"])

    _switch("user-b")
    r = await client.get(
        f"/api/projects/{pa}/economic-analyses/{e['id']}/cheers-report?format=docx"
    )
    assert r.status_code == 404


# ─── Cross-project containment ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_user_a_other_project_id_404s_economic_get(client):
    _switch("user-a")
    pa = await _make_project(client, "A")
    pb = await _make_project(client, "B")  # same user, different project
    ds = await _upload(client, pa)
    e = await _create_economic(client, pa, ds["id"])

    # Access through the WRONG project id should 404.
    r = await client.get(f"/api/projects/{pb}/economic-analyses/{e['id']}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_user_a_other_project_id_404s_economic_run(client):
    _switch("user-a")
    pa = await _make_project(client, "A")
    pb = await _make_project(client, "B")
    ds = await _upload(client, pa)
    e = await _create_economic(client, pa, ds["id"])

    r = await client.post(f"/api/projects/{pb}/economic-analyses/{e['id']}/run")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_user_a_other_project_id_404s_economic_patch(client):
    _switch("user-a")
    pa = await _make_project(client, "A")
    pb = await _make_project(client, "B")
    ds = await _upload(client, pa)
    e = await _create_economic(client, pa, ds["id"])

    r = await client.patch(
        f"/api/projects/{pb}/economic-analyses/{e['id']}",
        json={"name": "Wrong project"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_user_a_other_project_id_404s_economic_delete(client):
    _switch("user-a")
    pa = await _make_project(client, "A")
    pb = await _make_project(client, "B")
    ds = await _upload(client, pa)
    e = await _create_economic(client, pa, ds["id"])

    r = await client.delete(f"/api/projects/{pb}/economic-analyses/{e['id']}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_user_a_other_project_id_404s_economic_sensitivity(client):
    _switch("user-a")
    pa = await _make_project(client, "A")
    pb = await _make_project(client, "B")
    ds = await _upload(client, pa)
    e = await _create_economic(client, pa, ds["id"])

    r = await client.post(
        f"/api/projects/{pb}/economic-analyses/{e['id']}/sensitivity?type=dsa",
        json={"parameter_ranges": {"mean_cost_diff": {"low": 0, "high": 1}}},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_user_a_other_project_id_404s_economic_interpret(client):
    _switch("user-a")
    pa = await _make_project(client, "A")
    pb = await _make_project(client, "B")
    ds = await _upload(client, pa)
    e = await _create_economic(client, pa, ds["id"])

    r = await client.post(
        f"/api/projects/{pb}/economic-analyses/{e['id']}/interpret"
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_user_a_other_project_id_404s_economic_push(client):
    _switch("user-a")
    pa = await _make_project(client, "A")
    pb = await _make_project(client, "B")
    ds = await _upload(client, pa)
    e = await _create_economic(client, pa, ds["id"])

    r = await client.post(
        f"/api/projects/{pb}/economic-analyses/{e['id']}/push",
        json={"section": "Results"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_user_a_other_project_id_404s_cheers_report(client):
    _switch("user-a")
    pa = await _make_project(client, "A")
    pb = await _make_project(client, "B")
    ds = await _upload(client, pa)
    e = await _create_economic(client, pa, ds["id"])

    r = await client.get(
        f"/api/projects/{pb}/economic-analyses/{e['id']}/cheers-report"
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_user_b_list_returns_404_on_other_user_project(client):
    _switch("user-a")
    pa = await _make_project(client, "A")

    _switch("user-b")
    r = await client.get(f"/api/projects/{pa}/economic-analyses")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_user_a_economic_list_excludes_user_b_rows(client):
    _switch("user-a")
    pa = await _make_project(client, "A")
    ds_a = await _upload(client, pa)
    await _create_economic(client, pa, ds_a["id"])

    _switch("user-b")
    pb = await _make_project(client, "B")
    ds_b = await _upload(client, pb)
    await _create_economic(client, pb, ds_b["id"])

    # user-a's list contains exactly 1 row (their own).
    _switch("user-a")
    r = await client.get(f"/api/projects/{pa}/economic-analyses")
    assert r.status_code == 200
    assert len(r.json()) == 1


@pytest.mark.asyncio
async def test_utility_value_sets_is_unauthenticated_safe(client):
    """The catalogue endpoint is static + project-agnostic; both users see it."""
    _switch("user-a")
    r1 = await client.get("/api/utility-value-sets")
    _switch("user-b")
    r2 = await client.get("/api/utility-value-sets")
    assert r1.status_code == r2.status_code == 200
    assert r1.json() == r2.json()
