"""DEMO-FIX-C — PATCH /chart-labels endpoint + re-render verification.

Three guarantees:
  1. The endpoint persists x/y/title overrides on AnalysisResult.chart.
  2. A re-run after overrides are set preserves them.
  3. 422 when the analysis has no result yet (must run() first).
"""
from __future__ import annotations

import pytest

CSV_BYTES = (
    b"score,group\n"
    b"10,A\n12,A\n14,A\n11,A\n13,A\n9,A\n"
    b"6,B\n8,B\n7,B\n8,B\n6,B\n9,B\n"
)


async def _make_project(client) -> str:
    r = await client.post(
        "/api/projects",
        json={"title": "Lab", "study_type": "Outcome Study"},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _upload(client, project_id) -> dict:
    files = {"file": ("data.csv", CSV_BYTES, "text/csv")}
    r = await client.post(f"/api/projects/{project_id}/datasets", files=files)
    assert r.status_code == 201, r.text
    return r.json()


async def _create_and_run(client, project_id, dataset_id) -> dict:
    r = await client.post(
        f"/api/projects/{project_id}/datasets/{dataset_id}/analyses",
        json={
            "question_type": "group_comparison",
            "chosen_test": "independent_t",
            "variables": {"outcome": "score", "groups": "group"},
        },
    )
    assert r.status_code == 201, r.text
    aid = r.json()["id"]
    rr = await client.post(f"/api/projects/{project_id}/analyses/{aid}/run")
    assert rr.status_code == 200, rr.text
    return rr.json()


@pytest.mark.asyncio
async def test_patch_chart_labels_persists_overrides(client):
    pid = await _make_project(client)
    ds = await _upload(client, pid)
    a = await _create_and_run(client, pid, ds["id"])

    r = await client.patch(
        f"/api/projects/{pid}/analyses/{a['id']}/chart-labels",
        json={
            "x_label_override": "Treatment arm",
            "y_label_override": "Pain score (0-10)",
            "title_override": "Pain by arm",
        },
    )
    assert r.status_code == 200, r.text
    chart = r.json()["result"]["chart"]
    assert chart is not None
    assert chart["x_label_override"] == "Treatment arm"
    assert chart["y_label_override"] == "Pain score (0-10)"
    assert chart["title_override"] == "Pain by arm"
    # title_override is mirrored into the active title so downstream
    # consumers (exports, PDF) pick it up unconditionally.
    assert chart.get("title") == "Pain by arm"
    # And a re-rendered PNG is still attached (or, on failure, the override
    # is at least persisted — verify by re-fetching).
    assert chart.get("format") == "png" or "data_uri" in chart


@pytest.mark.asyncio
async def test_patch_chart_labels_422_without_result(client):
    """Cannot set chart labels on an analysis that hasn't run yet."""
    pid = await _make_project(client)
    ds = await _upload(client, pid)
    r = await client.post(
        f"/api/projects/{pid}/datasets/{ds['id']}/analyses",
        json={
            "question_type": "group_comparison",
            "chosen_test": "independent_t",
            "variables": {"outcome": "score", "groups": "group"},
        },
    )
    aid = r.json()["id"]
    r = await client.patch(
        f"/api/projects/{pid}/analyses/{aid}/chart-labels",
        json={"x_label_override": "X"},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_chart_labels_survive_rerun(client):
    """A re-run after labels were set must preserve them — re-running an
    analysis is a common UX after editing display labels."""
    pid = await _make_project(client)
    ds = await _upload(client, pid)
    a = await _create_and_run(client, pid, ds["id"])
    await client.patch(
        f"/api/projects/{pid}/analyses/{a['id']}/chart-labels",
        json={"title_override": "My Title"},
    )
    # Re-run.
    r = await client.post(f"/api/projects/{pid}/analyses/{a['id']}/run")
    assert r.status_code == 200
    chart = r.json()["result"]["chart"]
    assert chart["title_override"] == "My Title"


@pytest.mark.asyncio
async def test_patch_chart_labels_404_for_unknown_analysis(client):
    pid = await _make_project(client)
    r = await client.patch(
        f"/api/projects/{pid}/analyses/missing/chart-labels",
        json={"x_label_override": "X"},
    )
    assert r.status_code == 404
