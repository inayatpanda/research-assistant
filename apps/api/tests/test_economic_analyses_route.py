"""Phase 18 (MP18) — Health Economics route tests."""
from __future__ import annotations

import pytest


# A 12-row dataset with utility + cost + treatment columns.
CSV_DATA = (
    b"patient_id,treatment,cost_total,utility,time_months\n"
    + b"p1,anterior,1500,0.85,12\n"
    + b"p2,anterior,1700,0.82,12\n"
    + b"p3,anterior,1600,0.88,12\n"
    + b"p4,anterior,1800,0.80,12\n"
    + b"p5,anterior,1550,0.87,12\n"
    + b"p6,anterior,1650,0.83,12\n"
    + b"p7,control,1000,0.70,12\n"
    + b"p8,control,1100,0.65,12\n"
    + b"p9,control,1200,0.72,12\n"
    + b"p10,control,1050,0.68,12\n"
    + b"p11,control,1150,0.71,12\n"
    + b"p12,control,1080,0.69,12\n"
)


async def _make_project(client, title="EconProj") -> str:
    r = await client.post(
        "/api/projects",
        json={"title": title, "study_type": "Randomised Controlled Trial"},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _upload(client, pid: str) -> dict:
    files = {"file": ("cea.csv", CSV_DATA, "text/csv")}
    r = await client.post(f"/api/projects/{pid}/datasets", files=files)
    assert r.status_code == 201, r.text
    return r.json()


async def _create_economic(client, pid: str, did: str | None) -> dict:
    body = {
        "name": "Anterior vs control CEA",
        "dataset_id": did,
        "currency": "GBP",
        "time_horizon_months": 12,
        "perspective": "healthcare_system",
        "discount_rate_costs": 0.035,
        "discount_rate_qalys": 0.035,
        "wtp_thresholds": [20000, 30000],
        "utility_value_set": "direct",
        "bootstrap_n": 200,
        "seed": 42,
        "treatment_col": "treatment",
        "comparator_label": "control",
        "intervention_label": "anterior",
        "cost_columns": [
            {"col": "cost_total", "role": "cost_total"},
            {"col": "utility", "role": "qaly_weight"},
        ],
    }
    r = await client.post(f"/api/projects/{pid}/economic-analyses", json=body)
    assert r.status_code == 201, r.text
    return r.json()


@pytest.mark.asyncio
async def test_utility_value_sets_catalogue(client):
    r = await client.get("/api/utility-value-sets")
    assert r.status_code == 200
    keys = {entry["key"] for entry in r.json()}
    assert {"EQ5D_3L_UK", "EQ5D_5L_UK", "EQ5D_Y_DUTCH", "SF6D", "direct"} <= keys


@pytest.mark.asyncio
async def test_create_economic_analysis_happy_path(client):
    pid = await _make_project(client)
    ds = await _upload(client, pid)
    e = await _create_economic(client, pid, ds["id"])
    assert e["name"] == "Anterior vs control CEA"
    assert e["dataset_id"] == ds["id"]
    assert e["wtp_thresholds"] == [20000, 30000]
    assert e["result"] is None


@pytest.mark.asyncio
async def test_create_economic_analysis_404_missing_project(client):
    r = await client.post(
        "/api/projects/missing/economic-analyses",
        json={
            "name": "x",
            "treatment_col": "t",
            "comparator_label": "c",
            "intervention_label": "i",
        },
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_create_economic_analysis_404_missing_dataset(client):
    pid = await _make_project(client)
    r = await client.post(
        f"/api/projects/{pid}/economic-analyses",
        json={
            "name": "x",
            "dataset_id": "missing",
            "treatment_col": "t",
            "comparator_label": "c",
            "intervention_label": "i",
        },
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_list_economic_analyses(client):
    pid = await _make_project(client)
    ds = await _upload(client, pid)
    await _create_economic(client, pid, ds["id"])
    r = await client.get(f"/api/projects/{pid}/economic-analyses")
    assert r.status_code == 200
    assert len(r.json()) == 1


@pytest.mark.asyncio
async def test_get_economic_analysis(client):
    pid = await _make_project(client)
    ds = await _upload(client, pid)
    e = await _create_economic(client, pid, ds["id"])
    r = await client.get(f"/api/projects/{pid}/economic-analyses/{e['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == e["id"]


@pytest.mark.asyncio
async def test_get_economic_analysis_404(client):
    pid = await _make_project(client)
    r = await client.get(f"/api/projects/{pid}/economic-analyses/missing")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_update_economic_analysis(client):
    pid = await _make_project(client)
    ds = await _upload(client, pid)
    e = await _create_economic(client, pid, ds["id"])
    r = await client.patch(
        f"/api/projects/{pid}/economic-analyses/{e['id']}",
        json={"name": "Renamed CEA"},
    )
    assert r.status_code == 200
    assert r.json()["name"] == "Renamed CEA"


@pytest.mark.asyncio
async def test_delete_economic_analysis(client):
    pid = await _make_project(client)
    ds = await _upload(client, pid)
    e = await _create_economic(client, pid, ds["id"])
    r = await client.delete(f"/api/projects/{pid}/economic-analyses/{e['id']}")
    assert r.status_code == 204
    r2 = await client.get(f"/api/projects/{pid}/economic-analyses/{e['id']}")
    assert r2.status_code == 404


@pytest.mark.asyncio
async def test_run_economic_analysis_attaches_result(client):
    pid = await _make_project(client)
    ds = await _upload(client, pid)
    e = await _create_economic(client, pid, ds["id"])
    r = await client.post(
        f"/api/projects/{pid}/economic-analyses/{e['id']}/run"
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["result"] is not None
    res = body["result"]
    assert res["mean_cost_diff"] > 0  # anterior costs more than control
    assert res["mean_qaly_diff"] > 0  # anterior has higher utility
    # ICER should be in NE quadrant.
    assert res["dominance_status"] in {"northeast", "icer_calculated"}
    assert res["icer"] is not None
    assert res["plane_png_uri"].startswith("data:image/png;base64,")
    assert res["ceac_png_uri"].startswith("data:image/png;base64,")
    assert isinstance(res["ceac_data"], list) and len(res["ceac_data"]) > 0
    assert isinstance(res["plane_bootstrap"], list)


@pytest.mark.asyncio
async def test_run_economic_404_missing_analysis(client):
    pid = await _make_project(client)
    r = await client.post(
        f"/api/projects/{pid}/economic-analyses/missing/run"
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_run_economic_422_without_dataset(client):
    pid = await _make_project(client)
    e = await _create_economic(client, pid, None)
    r = await client.post(
        f"/api/projects/{pid}/economic-analyses/{e['id']}/run"
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_sensitivity_dsa_attaches_payload(client):
    pid = await _make_project(client)
    ds = await _upload(client, pid)
    e = await _create_economic(client, pid, ds["id"])
    await client.post(f"/api/projects/{pid}/economic-analyses/{e['id']}/run")
    r = await client.post(
        f"/api/projects/{pid}/economic-analyses/{e['id']}/sensitivity?type=dsa",
        json={
            "parameter_ranges": {
                "mean_cost_diff": {"low": 200, "high": 800},
                "mean_qaly_diff": {"low": 0.05, "high": 0.2},
            }
        },
    )
    assert r.status_code == 200, r.text
    sens = r.json()["result"]["sensitivity"]
    assert sens["type"] == "dsa"
    assert len(sens["results"]) == 2


@pytest.mark.asyncio
async def test_sensitivity_422_before_run(client):
    pid = await _make_project(client)
    ds = await _upload(client, pid)
    e = await _create_economic(client, pid, ds["id"])
    r = await client.post(
        f"/api/projects/{pid}/economic-analyses/{e['id']}/sensitivity?type=dsa",
        json={"parameter_ranges": {"mean_cost_diff": {"low": 0, "high": 1}}},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_interpret_attaches_prose_with_cite_token(client):
    pid = await _make_project(client)
    ds = await _upload(client, pid)
    e = await _create_economic(client, pid, ds["id"])
    await client.post(f"/api/projects/{pid}/economic-analyses/{e['id']}/run")
    r = await client.post(
        f"/api/projects/{pid}/economic-analyses/{e['id']}/interpret"
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ai_interpretation"]
    assert f"[CITE_dataset_{ds['id']}]" in body["ai_interpretation"]


@pytest.mark.asyncio
async def test_interpret_422_without_run(client):
    pid = await _make_project(client)
    ds = await _upload(client, pid)
    e = await _create_economic(client, pid, ds["id"])
    r = await client.post(
        f"/api/projects/{pid}/economic-analyses/{e['id']}/interpret"
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_push_economic_to_manuscript(client):
    pid = await _make_project(client)
    ds = await _upload(client, pid)
    e = await _create_economic(client, pid, ds["id"])
    await client.post(f"/api/projects/{pid}/economic-analyses/{e['id']}/run")
    await client.post(
        f"/api/projects/{pid}/economic-analyses/{e['id']}/interpret"
    )
    r = await client.post(
        f"/api/projects/{pid}/economic-analyses/{e['id']}/push",
        json={"section": "Results"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["section_name"] == "Results"
    assert 'class="economic-analysis"' in body["content"]
    assert "data:image/png;base64," in body["content"]


@pytest.mark.asyncio
async def test_push_economic_idempotent_replace_by_class(client):
    pid = await _make_project(client)
    ds = await _upload(client, pid)
    e = await _create_economic(client, pid, ds["id"])
    await client.post(f"/api/projects/{pid}/economic-analyses/{e['id']}/run")
    await client.post(
        f"/api/projects/{pid}/economic-analyses/{e['id']}/interpret"
    )
    r1 = await client.post(
        f"/api/projects/{pid}/economic-analyses/{e['id']}/push",
        json={"section": "Results"},
    )
    r2 = await client.post(
        f"/api/projects/{pid}/economic-analyses/{e['id']}/push",
        json={"section": "Results"},
    )
    assert r1.status_code == 200
    assert r2.status_code == 200
    # Should have exactly one figure block (not two) after re-push.
    content = r2.json()["content"]
    assert content.count('class="economic-analysis"') == 1


@pytest.mark.asyncio
async def test_cheers_report_docx_streams(client):
    pid = await _make_project(client)
    ds = await _upload(client, pid)
    e = await _create_economic(client, pid, ds["id"])
    await client.post(f"/api/projects/{pid}/economic-analyses/{e['id']}/run")
    r = await client.get(
        f"/api/projects/{pid}/economic-analyses/{e['id']}/cheers-report?format=docx"
    )
    assert r.status_code == 200
    # DOCX zip signature
    assert r.content[:2] == b"PK"


@pytest.mark.asyncio
async def test_cheers_report_pdf_streams(client):
    pid = await _make_project(client)
    ds = await _upload(client, pid)
    e = await _create_economic(client, pid, ds["id"])
    await client.post(f"/api/projects/{pid}/economic-analyses/{e['id']}/run")
    r = await client.get(
        f"/api/projects/{pid}/economic-analyses/{e['id']}/cheers-report?format=pdf"
    )
    assert r.status_code == 200
    # PDF signature
    assert r.content[:4] == b"%PDF"
