"""DEMO-FIX-C — Display-label PATCH endpoint + GET propagation tests.

The endpoint
  PATCH /api/projects/{pid}/datasets/{did}/variables/{vid}/display-label

sets a free-text label that the runner ignores but chart axes, AI prose
and exports honour. The canonical ``name`` stays Python-identifier-safe;
this is purely metadata.
"""
from __future__ import annotations

import pytest

CSV_BYTES = b"age,sex,bmi\n45,M,24.1\n50,F,22.0\n42,M,27.5\n55,F,21.0\n"


async def _make_project(client) -> str:
    r = await client.post(
        "/api/projects",
        json={"title": "DLab", "study_type": "Outcome Study"},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _upload_csv(client, project_id: str) -> dict:
    files = {"file": ("data.csv", CSV_BYTES, "text/csv")}
    r = await client.post(f"/api/projects/{project_id}/datasets", files=files)
    assert r.status_code == 201, r.text
    return r.json()


@pytest.mark.asyncio
async def test_display_label_defaults_to_canonical_name(client):
    """When the raw header is identifier-safe, display_label equals name."""
    pid = await _make_project(client)
    ds = await _upload_csv(client, pid)
    for v in ds["variables"]:
        assert v["display_label"] == v["name"], v


@pytest.mark.asyncio
async def test_patch_display_label_updates_field(client):
    pid = await _make_project(client)
    ds = await _upload_csv(client, pid)
    age = next(v for v in ds["variables"] if v["name"] == "age")
    r = await client.patch(
        f"/api/projects/{pid}/datasets/{ds['id']}/variables/{age['id']}"
        "/display-label",
        json={"display_label": "Age (years)"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["display_label"] == "Age (years)"
    # Canonical name is unchanged.
    assert r.json()["name"] == "age"


@pytest.mark.asyncio
async def test_patch_display_label_persists_on_get(client):
    pid = await _make_project(client)
    ds = await _upload_csv(client, pid)
    sex = next(v for v in ds["variables"] if v["name"] == "sex")
    await client.patch(
        f"/api/projects/{pid}/datasets/{ds['id']}/variables/{sex['id']}"
        "/display-label",
        json={"display_label": "Patient sex"},
    )
    r = await client.get(f"/api/projects/{pid}/datasets/{ds['id']}")
    assert r.status_code == 200
    by_name = {v["name"]: v for v in r.json()["variables"]}
    assert by_name["sex"]["display_label"] == "Patient sex"
    # Other vars unaffected.
    assert by_name["age"]["display_label"] == "age"


@pytest.mark.asyncio
async def test_patch_display_label_empty_falls_back_to_canonical(client):
    """An empty / whitespace-only body falls back to the canonical name."""
    pid = await _make_project(client)
    ds = await _upload_csv(client, pid)
    age = next(v for v in ds["variables"] if v["name"] == "age")
    # First set it to something, then send "" to clear.
    await client.patch(
        f"/api/projects/{pid}/datasets/{ds['id']}/variables/{age['id']}"
        "/display-label",
        json={"display_label": "Age (years)"},
    )
    r = await client.patch(
        f"/api/projects/{pid}/datasets/{ds['id']}/variables/{age['id']}"
        "/display-label",
        json={"display_label": "   "},
    )
    assert r.status_code == 200
    # Whitespace-only → coerced back to canonical.
    assert r.json()["display_label"] == "age"


@pytest.mark.asyncio
async def test_patch_display_label_404_for_unknown_variable(client):
    pid = await _make_project(client)
    ds = await _upload_csv(client, pid)
    r = await client.patch(
        f"/api/projects/{pid}/datasets/{ds['id']}/variables/nope/display-label",
        json={"display_label": "X"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_patch_display_label_isolated_across_projects(client):
    """Editing in project A must not affect project B."""
    pid_a = await _make_project(client)
    pid_b = await _make_project(client)
    ds_a = await _upload_csv(client, pid_a)
    ds_b = await _upload_csv(client, pid_b)
    var_a = next(v for v in ds_a["variables"] if v["name"] == "age")
    var_b = next(v for v in ds_b["variables"] if v["name"] == "age")

    await client.patch(
        f"/api/projects/{pid_a}/datasets/{ds_a['id']}/variables/{var_a['id']}"
        "/display-label",
        json={"display_label": "Age (project A)"},
    )

    r_a = await client.get(f"/api/projects/{pid_a}/datasets/{ds_a['id']}")
    r_b = await client.get(f"/api/projects/{pid_b}/datasets/{ds_b['id']}")
    by_a = {v["name"]: v for v in r_a.json()["variables"]}
    by_b = {v["name"]: v for v in r_b.json()["variables"]}
    assert by_a["age"]["display_label"] == "Age (project A)"
    # B still has the default canonical fallback.
    assert by_b["age"]["display_label"] == "age"
    # Crucially, the variable ids differ (no cross-project leakage).
    assert var_a["id"] != var_b["id"]
