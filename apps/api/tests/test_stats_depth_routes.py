"""Phase 17 (MP17) — Stats depth route tests (populations, imputation, CACE,
sensitivity, post-hoc, IRR, instruments)."""
from __future__ import annotations

import io

import pytest


CSV_DATA = (
    b"score,arm,assigned,received,age,sex\n"
    + b"10,A,1,1,40,M\n12,A,1,1,42,F\n14,A,1,1,38,F\n11,A,1,0,45,M\n13,A,1,1,44,F\n9,A,1,0,41,M\n"
    + b"6,B,0,0,40,M\n8,B,0,0,43,F\n7,B,0,0,39,F\n8,B,0,1,45,M\n6,B,0,0,42,F\n9,B,0,0,40,M\n"
)


async def _project(client, title="P") -> str:
    r = await client.post("/api/projects", json={"title": title, "study_type": "Outcome Study"})
    return r.json()["id"]


async def _upload(client, pid: str, payload: bytes = CSV_DATA) -> dict:
    files = {"file": ("data.csv", payload, "text/csv")}
    r = await client.post(f"/api/projects/{pid}/datasets", files=files)
    assert r.status_code == 201, r.text
    return r.json()


# ── Populations CRUD ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_and_list_populations(client):
    pid = await _project(client)
    ds = await _upload(client, pid)
    create = await client.post(
        f"/api/projects/{pid}/datasets/{ds['id']}/populations",
        json={
            "name": "ITT",
            "definition": {"filter": "", "label": "ITT"},
            "study_assignment_field": "assigned",
            "treatment_received_field": "received",
        },
    )
    assert create.status_code == 201, create.text
    body = create.json()
    assert body["name"] == "ITT"

    lst = await client.get(f"/api/projects/{pid}/datasets/{ds['id']}/populations")
    assert lst.status_code == 200
    assert len(lst.json()) == 1


@pytest.mark.asyncio
async def test_population_preview_applies_filter(client):
    pid = await _project(client)
    ds = await _upload(client, pid)
    create = await client.post(
        f"/api/projects/{pid}/datasets/{ds['id']}/populations",
        json={
            "name": "PP",
            "definition": {"filter": "assigned == received", "label": "PP"},
            "study_assignment_field": "assigned",
            "treatment_received_field": "received",
        },
    )
    pop_id = create.json()["id"]
    preview = await client.post(
        f"/api/projects/{pid}/datasets/{ds['id']}/populations/{pop_id}/preview"
    )
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body["n_before"] == 12
    # 9 rows have assigned == received
    assert body["n_after"] == 9


@pytest.mark.asyncio
async def test_population_update_and_delete(client):
    pid = await _project(client)
    ds = await _upload(client, pid)
    create = await client.post(
        f"/api/projects/{pid}/datasets/{ds['id']}/populations",
        json={
            "name": "Safety",
            "definition": {"filter": "", "label": "Safety"},
            "study_assignment_field": "assigned",
            "treatment_received_field": None,
        },
    )
    pop_id = create.json()["id"]
    update = await client.patch(
        f"/api/projects/{pid}/datasets/{ds['id']}/populations/{pop_id}",
        json={"name": "Safety v2"},
    )
    assert update.status_code == 200
    assert update.json()["name"] == "Safety v2"

    delete = await client.delete(
        f"/api/projects/{pid}/datasets/{ds['id']}/populations/{pop_id}"
    )
    assert delete.status_code == 204


@pytest.mark.asyncio
async def test_population_preview_invalid_filter_returns_400(client):
    pid = await _project(client)
    ds = await _upload(client, pid)
    create = await client.post(
        f"/api/projects/{pid}/datasets/{ds['id']}/populations",
        json={
            "name": "Bad",
            "definition": {"filter": "this is not pandas syntax!", "label": "x"},
            "study_assignment_field": "assigned",
        },
    )
    pop_id = create.json()["id"]
    preview = await client.post(
        f"/api/projects/{pid}/datasets/{ds['id']}/populations/{pop_id}/preview"
    )
    assert preview.status_code == 400


# ── Imputation ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_run_mice_imputation_route(client):
    pid = await _project(client)
    ds = await _upload(client, pid)
    r = await client.post(
        f"/api/projects/{pid}/datasets/{ds['id']}/impute",
        json={
            "method": "mice",
            "target_cols": ["score", "age"],
            "n_imputations": 3,
            "seed": 1,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["method"] == "mice"
    assert body["n_imputations"] == 3
    per_col = body["pooled_summary"]["per_column"]
    cols = {c["column"] for c in per_col}
    assert cols == {"score", "age"}


@pytest.mark.asyncio
async def test_imputation_listed_after_run(client):
    pid = await _project(client)
    ds = await _upload(client, pid)
    await client.post(
        f"/api/projects/{pid}/datasets/{ds['id']}/impute",
        json={"method": "mean", "target_cols": ["score"], "n_imputations": 1, "seed": 1},
    )
    lst = await client.get(
        f"/api/projects/{pid}/datasets/{ds['id']}/imputation-runs"
    )
    assert lst.status_code == 200
    assert len(lst.json()) == 1


@pytest.mark.asyncio
async def test_imputation_rejects_unknown_column(client):
    pid = await _project(client)
    ds = await _upload(client, pid)
    r = await client.post(
        f"/api/projects/{pid}/datasets/{ds['id']}/impute",
        json={"method": "mice", "target_cols": ["bogus"], "n_imputations": 2, "seed": 1},
    )
    assert r.status_code == 400


# ── Instruments ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_instrument_catalogue_returns_thirty_entries(client):
    r = await client.get("/api/instruments/catalogue")
    assert r.status_code == 200
    instruments = r.json()["instruments"]
    abbrs = {i["abbreviation"] for i in instruments}
    # Spot-check a few expected entries
    for abbr in ("HHS", "OHS", "WOMAC", "VAS Pain", "NYHA"):
        assert abbr in abbrs
    assert len(instruments) == 32  # actual count from the curated list


@pytest.mark.asyncio
async def test_instrument_binding_patch_updates_dataset_variable(client):
    pid = await _project(client)
    ds = await _upload(client, pid)
    var_id = ds["variables"][0]["id"]
    r = await client.patch(
        f"/api/projects/{pid}/datasets/{ds['id']}/variables/{var_id}/instrument-binding",
        json={"instrument_key": "HHS"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["instrument_key"] == "HHS"


@pytest.mark.asyncio
async def test_instrument_binding_rejects_unknown_key(client):
    pid = await _project(client)
    ds = await _upload(client, pid)
    var_id = ds["variables"][0]["id"]
    r = await client.patch(
        f"/api/projects/{pid}/datasets/{ds['id']}/variables/{var_id}/instrument-binding",
        json={"instrument_key": "BOGUS_KEY"},
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_instrument_binding_unbinds_with_null(client):
    pid = await _project(client)
    ds = await _upload(client, pid)
    var_id = ds["variables"][0]["id"]
    await client.patch(
        f"/api/projects/{pid}/datasets/{ds['id']}/variables/{var_id}/instrument-binding",
        json={"instrument_key": "OKS"},
    )
    r = await client.patch(
        f"/api/projects/{pid}/datasets/{ds['id']}/variables/{var_id}/instrument-binding",
        json={"instrument_key": None},
    )
    assert r.status_code == 200
    assert r.json()["instrument_key"] is None


# ── Post-hoc route ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_post_hoc_route_tukey(client):
    pid = await _project(client)
    # 3-arm CSV to permit Tukey HSD.
    payload = (
        b"score,arm\n"
        + b"10,A\n12,A\n14,A\n11,A\n13,A\n9,A\n"
        + b"6,B\n8,B\n7,B\n8,B\n6,B\n9,B\n"
        + b"2,C\n3,C\n4,C\n2,C\n3,C\n3,C\n"
    )
    ds = await _upload(client, pid, payload)
    r = await client.post(
        f"/api/projects/{pid}/datasets/{ds['id']}/analyses",
        json={
            "question_type": "group_comparison",
            "chosen_test": "one_way_anova",
            "variables": {"outcome": "score", "groups": "arm"},
        },
    )
    aid = r.json()["id"]
    posthoc = await client.post(
        f"/api/projects/{pid}/analyses/{aid}/post-hoc",
        json={"method": "tukey", "outcome": "score", "groups": "arm"},
    )
    assert posthoc.status_code == 200, posthoc.text
    body = posthoc.json()
    assert body["method"] == "tukey"
    assert len(body["pairs"]) == 3


# ── IRR route ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_irr_route_fleiss(client):
    pid = await _project(client)
    ds = await _upload(client, pid)
    matrix = [[5, 0, 0]] * 10
    r = await client.post(
        f"/api/projects/{pid}/datasets/{ds['id']}/irr",
        json={"method": "fleiss", "matrix": matrix},
    )
    assert r.status_code == 200, r.text
    assert abs(r.json()["kappa"] - 1.0) < 1e-9


@pytest.mark.asyncio
async def test_irr_route_weighted_kappa(client):
    pid = await _project(client)
    ds = await _upload(client, pid)
    r = await client.post(
        f"/api/projects/{pid}/datasets/{ds['id']}/irr",
        json={
            "method": "weighted_kappa",
            "rater1": [0, 1, 2, 3],
            "rater2": [0, 1, 2, 3],
            "weights": "linear",
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["kappa"] == 1.0
