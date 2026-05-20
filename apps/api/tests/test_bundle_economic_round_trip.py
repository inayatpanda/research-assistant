"""Phase 18 (MP18) — Bundle export/import round-trip for the economics tables."""
from __future__ import annotations

import json

import pytest


CSV_BYTES = (
    b"patient_id,treatment,cost_total,utility\n"
    + b"p1,anterior,1500,0.85\np2,anterior,1700,0.82\n"
    + b"p3,control,1000,0.70\np4,control,1100,0.65\n"
)


async def _project(client) -> str:
    r = await client.post(
        "/api/projects",
        json={"title": "Bundle MP18", "study_type": "Randomised Controlled Trial"},
    )
    return r.json()["id"]


async def _upload(client, pid: str) -> dict:
    files = {"file": ("data.csv", CSV_BYTES, "text/csv")}
    r = await client.post(f"/api/projects/{pid}/datasets", files=files)
    return r.json()


@pytest.mark.asyncio
async def test_bundle_round_trip_carries_economic_analyses(client):
    pid = await _project(client)
    ds = await _upload(client, pid)
    body = {
        "name": "CEA",
        "dataset_id": ds["id"],
        "treatment_col": "treatment",
        "comparator_label": "control",
        "intervention_label": "anterior",
        "cost_columns": [
            {"col": "cost_total", "role": "cost_total"},
            {"col": "utility", "role": "qaly_weight"},
        ],
        "bootstrap_n": 100,
    }
    e = await client.post(f"/api/projects/{pid}/economic-analyses", json=body)
    assert e.status_code == 201, e.text
    eid = e.json()["id"]
    await client.post(f"/api/projects/{pid}/economic-analyses/{eid}/run")

    # Export.
    exp = await client.post(f"/api/projects/{pid}/export/bundle")
    bundle = exp.json()
    assert len(bundle["economic_analyses"]) == 1
    assert bundle["economic_analyses"][0]["name"] == "CEA"
    assert len(bundle["economic_results"]) == 1
    assert bundle["economic_results"][0]["plane_png_uri"].startswith(
        "data:image/png;base64,"
    )

    # Import into a fresh project.
    imp_resp = await client.post(
        "/api/projects/import/bundle",
        files={
            "file": (
                "bundle.json",
                json.dumps(bundle).encode("utf-8"),
                "application/json",
            )
        },
    )
    assert imp_resp.status_code in (200, 201), imp_resp.text
    counts = imp_resp.json().get("counts", imp_resp.json())
    assert counts["economic_analyses"] == 1
    assert counts["economic_results"] == 1


@pytest.mark.asyncio
async def test_bundle_round_trip_handles_economic_without_result(client):
    """An economic analysis created but never run still round-trips (no result row)."""
    pid = await _project(client)
    ds = await _upload(client, pid)
    body = {
        "name": "CEA-noresult",
        "dataset_id": ds["id"],
        "treatment_col": "treatment",
        "comparator_label": "control",
        "intervention_label": "anterior",
        "cost_columns": [{"col": "cost_total", "role": "cost_total"}],
    }
    await client.post(f"/api/projects/{pid}/economic-analyses", json=body)
    exp = await client.post(f"/api/projects/{pid}/export/bundle")
    bundle = exp.json()
    assert len(bundle["economic_analyses"]) == 1
    assert len(bundle["economic_results"]) == 0

    imp_resp = await client.post(
        "/api/projects/import/bundle",
        files={
            "file": (
                "bundle.json",
                json.dumps(bundle).encode("utf-8"),
                "application/json",
            )
        },
    )
    counts = imp_resp.json().get("counts", imp_resp.json())
    assert counts["economic_analyses"] == 1
    assert counts["economic_results"] == 0
