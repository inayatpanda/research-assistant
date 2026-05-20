"""DEMO-FIX-D HIGH-3 — Op-add type validation tests.

Adding a numeric-only op (``log_transform``, ``z_score``, ...) to a
non-numeric column must return 422 with a user-readable message at the
moment the user clicks "Add", not at runner time deep inside numpy.
"""
from __future__ import annotations

import pytest

# Two-column dataset: ``score`` is numeric, ``bmi_group`` is nominal.
CSV_BYTES = (
    b"score,bmi_group\n"
    b"22.1,normal\n"
    b"25.6,normal\n"
    b"29.4,high_bmi\n"
    b"33.0,high_bmi\n"
    b"18.0,low_bmi\n"
)


async def _project_dataset(client) -> tuple[str, str, dict[str, str]]:
    r = await client.post(
        "/api/projects", json={"title": "T", "study_type": "Outcome Study"}
    )
    pid = r.json()["id"]
    r = await client.post(
        f"/api/projects/{pid}/datasets",
        files={"file": ("d.csv", CSV_BYTES, "text/csv")},
    )
    did = r.json()["id"]
    # Map var name → id for type patches.
    ds = (await client.get(f"/api/projects/{pid}/datasets/{did}")).json()
    by_name = {v["name"]: v["id"] for v in ds["variables"]}
    return pid, did, by_name


@pytest.mark.asyncio
async def test_log_transform_on_nominal_column_returns_422(client):
    pid, did, by_name = await _project_dataset(client)
    # bmi_group is auto-inferred as nominal; pin the user_type to nominal
    # so the test is robust against inference tweaks.
    await client.patch(
        f"/api/projects/{pid}/datasets/{did}/variables/{by_name['bmi_group']}",
        json={"user_type": "nominal"},
    )

    r = await client.post(
        f"/api/projects/{pid}/datasets/{did}/transformations",
        json={
            "op_type": "log_transform",
            "op_args": {
                "column": "bmi_group",
                "new_column": "log_bmi_group",
                "base": "e",
            },
        },
    )
    assert r.status_code == 422, r.text
    detail = r.json()["detail"]
    assert "numeric" in detail.lower()
    assert "bmi_group" in detail
    assert "Nominal" in detail


@pytest.mark.asyncio
async def test_z_score_on_nominal_column_returns_422(client):
    """``z_score`` shares the numeric-only contract with ``log_transform``."""
    pid, did, by_name = await _project_dataset(client)
    await client.patch(
        f"/api/projects/{pid}/datasets/{did}/variables/{by_name['bmi_group']}",
        json={"user_type": "nominal"},
    )
    r = await client.post(
        f"/api/projects/{pid}/datasets/{did}/transformations",
        json={
            "op_type": "z_score",
            "op_args": {"column": "bmi_group", "new_column": "z_bmi"},
        },
    )
    assert r.status_code == 422, r.text
    detail = r.json()["detail"]
    assert "bmi_group" in detail
    assert "numeric" in detail.lower()


@pytest.mark.asyncio
async def test_log_transform_on_numeric_column_succeeds(client):
    """Sanity: validation must NOT reject the happy path."""
    pid, did, by_name = await _project_dataset(client)
    await client.patch(
        f"/api/projects/{pid}/datasets/{did}/variables/{by_name['score']}",
        json={"user_type": "numeric"},
    )
    r = await client.post(
        f"/api/projects/{pid}/datasets/{did}/transformations",
        json={
            "op_type": "log_transform",
            "op_args": {
                "column": "score",
                "new_column": "log_score",
                "base": "e",
            },
        },
    )
    assert r.status_code == 201, r.text


@pytest.mark.asyncio
async def test_patch_to_nominal_column_returns_422(client):
    """Editing an existing log_transform to point at a nominal column also 422s."""
    pid, did, by_name = await _project_dataset(client)
    await client.patch(
        f"/api/projects/{pid}/datasets/{did}/variables/{by_name['bmi_group']}",
        json={"user_type": "nominal"},
    )
    await client.patch(
        f"/api/projects/{pid}/datasets/{did}/variables/{by_name['score']}",
        json={"user_type": "numeric"},
    )
    # Create on numeric column (happy path).
    r = await client.post(
        f"/api/projects/{pid}/datasets/{did}/transformations",
        json={
            "op_type": "log_transform",
            "op_args": {
                "column": "score",
                "new_column": "log_score",
                "base": "e",
            },
        },
    )
    tid = r.json()["id"]
    # Try to repoint at the nominal column.
    r = await client.patch(
        f"/api/projects/{pid}/datasets/{did}/transformations/{tid}",
        json={
            "op_args": {
                "column": "bmi_group",
                "new_column": "log_bmi",
                "base": "e",
            }
        },
    )
    assert r.status_code == 422, r.text
    assert "bmi_group" in r.json()["detail"]
