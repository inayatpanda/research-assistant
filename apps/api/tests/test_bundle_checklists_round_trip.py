"""Phase 20 (MP20) — Bundle export/import round-trip for ``checklist_runs``."""
from __future__ import annotations

import json

import pytest


async def _project(client) -> str:
    r = await client.post(
        "/api/projects",
        json={"title": "Bundle MP20", "study_type": "Randomised Controlled Trial"},
    )
    return r.json()["id"]


@pytest.mark.asyncio
async def test_bundle_round_trip_carries_checklist_runs(client) -> None:
    pid = await _project(client)

    # Create two runs with patched statuses.
    r = await client.post(
        f"/api/projects/{pid}/checklists",
        json={"checklist_key": "CONSORT_2010", "title": "v1 to JBJS"},
    )
    rid_1 = r.json()["id"]
    await client.patch(
        f"/api/projects/{pid}/checklists/{rid_1}/items/1",
        json={"status": "pass", "comment": "Title fine"},
    )
    r = await client.post(
        f"/api/projects/{pid}/checklists",
        json={"checklist_key": "CARE", "title": "case 1"},
    )
    rid_2 = r.json()["id"]
    await client.patch(
        f"/api/projects/{pid}/checklists/{rid_2}/items/1",
        json={"status": "fail"},
    )

    # Export.
    exp = await client.post(f"/api/projects/{pid}/export/bundle")
    bundle = exp.json()
    assert len(bundle["checklist_runs"]) == 2
    keys = sorted(c["checklist_key"] for c in bundle["checklist_runs"])
    assert keys == ["CARE", "CONSORT_2010"]
    # First run should still carry the user-patched status.
    consort_run = next(
        c for c in bundle["checklist_runs"] if c["checklist_key"] == "CONSORT_2010"
    )
    assert any(
        i.get("status") == "pass" and i.get("comment") == "Title fine"
        for i in consort_run["items"]
    )

    # Re-import the bundle into a fresh project.
    imp = await client.post(
        "/api/projects/import/bundle",
        files={
            "file": (
                "bundle.json",
                json.dumps(bundle).encode("utf-8"),
                "application/json",
            )
        },
    )
    assert imp.status_code in (200, 201), imp.text
    counts = imp.json().get("counts", imp.json())
    assert counts["checklist_runs"] == 2


@pytest.mark.asyncio
async def test_bundle_round_trip_handles_missing_checklist_runs_array(client) -> None:
    """An older bundle without a ``checklist_runs`` key still imports cleanly."""
    pid = await _project(client)
    exp = await client.post(f"/api/projects/{pid}/export/bundle")
    bundle = exp.json()
    # Strip the array to mimic a pre-MP20 export.
    bundle.pop("checklist_runs", None)
    imp = await client.post(
        "/api/projects/import/bundle",
        files={
            "file": (
                "bundle.json",
                json.dumps(bundle).encode("utf-8"),
                "application/json",
            )
        },
    )
    assert imp.status_code in (200, 201), imp.text
    counts = imp.json().get("counts", imp.json())
    assert counts["checklist_runs"] == 0
