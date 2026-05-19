"""Phase 17 (MP17) — Bundle export/import round-trip for stats-depth tables."""
from __future__ import annotations

import json

import pytest


CSV_BYTES = b"score,arm\n10,A\n12,A\n6,B\n8,B\n"


async def _project(client) -> str:
    r = await client.post(
        "/api/projects", json={"title": "Bundle MP17", "study_type": "Outcome Study"}
    )
    return r.json()["id"]


async def _upload(client, pid: str) -> dict:
    files = {"file": ("data.csv", CSV_BYTES, "text/csv")}
    r = await client.post(f"/api/projects/{pid}/datasets", files=files)
    return r.json()


@pytest.mark.asyncio
async def test_bundle_round_trip_carries_population_and_imputation_runs(client):
    pid = await _project(client)
    ds = await _upload(client, pid)
    # Create a population.
    pop = await client.post(
        f"/api/projects/{pid}/datasets/{ds['id']}/populations",
        json={
            "name": "ITT",
            "definition": {"filter": "", "label": "ITT"},
            "study_assignment_field": "arm",
        },
    )
    assert pop.status_code == 201, pop.text
    # Create an imputation run.
    imp = await client.post(
        f"/api/projects/{pid}/datasets/{ds['id']}/impute",
        json={"method": "mean", "target_cols": ["score"], "n_imputations": 1, "seed": 1},
    )
    assert imp.status_code == 200, imp.text

    # Export the bundle.
    exp = await client.post(f"/api/projects/{pid}/export/bundle")
    assert exp.status_code == 200, exp.text
    bundle = exp.json()
    assert len(bundle["analysis_populations"]) == 1
    assert bundle["analysis_populations"][0]["name"] == "ITT"
    assert len(bundle["imputation_runs"]) == 1
    assert bundle["imputation_runs"][0]["method"] == "mean"

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
    summary = imp_resp.json()
    counts = summary.get("counts", summary)
    assert counts["analysis_populations"] == 1
    assert counts["imputation_runs"] == 1


@pytest.mark.asyncio
async def test_bundle_export_includes_lock_fields_on_plans(client):
    pid = await _project(client)
    p = await client.post(
        f"/api/projects/{pid}/analysis-plans",
        json={"name": "P", "steps": [{"type": "test", "args": {}}]},
    )
    plan_id = p.json()["id"]
    await client.post(f"/api/projects/{pid}/analysis-plans/{plan_id}/lock")
    exp = await client.post(f"/api/projects/{pid}/export/bundle")
    plan_in_bundle = exp.json()["analysis_plans"][0]
    assert plan_in_bundle["is_locked"] is True
    assert plan_in_bundle["integrity_hash"] is not None
    assert plan_in_bundle["locked_at"] is not None
