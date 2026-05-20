"""Phase 13 (MP13) — DatasetTransformation route tests."""
from __future__ import annotations

import pytest

CSV_BYTES = b"x,y,g\n1,10,a\n2,20,b\n3,30,a\n4,40,b\n5,50,a\n"


async def _project_dataset(client) -> tuple[str, str]:
    r = await client.post(
        "/api/projects", json={"title": "T", "study_type": "Outcome Study"}
    )
    project_id = r.json()["id"]
    r = await client.post(
        f"/api/projects/{project_id}/datasets",
        files={"file": ("d.csv", CSV_BYTES, "text/csv")},
    )
    return project_id, r.json()["id"]


@pytest.mark.asyncio
async def test_create_lists_one_transformation(client):
    pid, did = await _project_dataset(client)
    r = await client.post(
        f"/api/projects/{pid}/datasets/{did}/transformations",
        json={
            "op_type": "filter",
            "op_args": {"column": "g", "op": "==", "value": "a"},
            "label": "keep group a",
        },
    )
    assert r.status_code == 201, r.text
    row = r.json()
    assert row["op_type"] == "filter"
    assert row["position"] == 0
    assert row["label"] == "keep group a"

    r = await client.get(f"/api/projects/{pid}/datasets/{did}/transformations")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 1
    assert rows[0]["id"] == row["id"]


@pytest.mark.asyncio
async def test_multiple_positions_are_dense(client):
    pid, did = await _project_dataset(client)
    for label, op_type, args in [
        ("keep g=a", "filter", {"column": "g", "op": "==", "value": "a"}),
        ("z-score x", "z_score", {"column": "x", "new_column": "z_x"}),
        ("drop na", "drop_na", {"columns": None}),
    ]:
        r = await client.post(
            f"/api/projects/{pid}/datasets/{did}/transformations",
            json={"op_type": op_type, "op_args": args, "label": label},
        )
        assert r.status_code == 201, r.text
    rows = (
        await client.get(f"/api/projects/{pid}/datasets/{did}/transformations")
    ).json()
    assert [r["position"] for r in rows] == [0, 1, 2]
    assert [r["label"] for r in rows] == ["keep g=a", "z-score x", "drop na"]


@pytest.mark.asyncio
async def test_patch_op_args(client):
    pid, did = await _project_dataset(client)
    r = await client.post(
        f"/api/projects/{pid}/datasets/{did}/transformations",
        json={"op_type": "filter", "op_args": {"column": "g", "op": "==", "value": "a"}},
    )
    tid = r.json()["id"]
    r = await client.patch(
        f"/api/projects/{pid}/datasets/{did}/transformations/{tid}",
        json={"op_args": {"column": "g", "op": "==", "value": "b"}, "label": "b only"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["op_args"]["value"] == "b"
    assert body["label"] == "b only"


@pytest.mark.asyncio
async def test_delete_densifies_positions(client):
    pid, did = await _project_dataset(client)
    ids: list[str] = []
    for op_type, args in [
        ("filter", {"column": "g", "op": "==", "value": "a"}),
        ("z_score", {"column": "x", "new_column": "z_x"}),
        ("drop_na", {"columns": None}),
    ]:
        r = await client.post(
            f"/api/projects/{pid}/datasets/{did}/transformations",
            json={"op_type": op_type, "op_args": args},
        )
        ids.append(r.json()["id"])
    # Delete the middle row.
    r = await client.delete(
        f"/api/projects/{pid}/datasets/{did}/transformations/{ids[1]}"
    )
    assert r.status_code == 204
    rows = (
        await client.get(f"/api/projects/{pid}/datasets/{did}/transformations")
    ).json()
    assert [r["position"] for r in rows] == [0, 1]
    assert [r["op_type"] for r in rows] == ["filter", "drop_na"]


@pytest.mark.asyncio
async def test_reorder_replaces_full_ordering(client):
    pid, did = await _project_dataset(client)
    ids: list[str] = []
    for op_type, args in [
        ("filter", {"column": "g", "op": "==", "value": "a"}),
        ("z_score", {"column": "x", "new_column": "z_x"}),
        ("drop_na", {"columns": None}),
    ]:
        r = await client.post(
            f"/api/projects/{pid}/datasets/{did}/transformations",
            json={"op_type": op_type, "op_args": args},
        )
        ids.append(r.json()["id"])
    reversed_ids = list(reversed(ids))
    r = await client.post(
        f"/api/projects/{pid}/datasets/{did}/transformations/reorder",
        json={"ids": reversed_ids},
    )
    assert r.status_code == 200, r.text
    rows = r.json()
    assert [r["id"] for r in rows] == reversed_ids
    assert [r["position"] for r in rows] == [0, 1, 2]


@pytest.mark.asyncio
async def test_reorder_rejects_mismatched_ids(client):
    pid, did = await _project_dataset(client)
    r = await client.post(
        f"/api/projects/{pid}/datasets/{did}/transformations",
        json={"op_type": "drop_na", "op_args": {"columns": None}},
    )
    real_id = r.json()["id"]
    r = await client.post(
        f"/api/projects/{pid}/datasets/{did}/transformations/reorder",
        json={"ids": [real_id, "ghost-id"]},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_unknown_dataset_404(client):
    r = await client.post(
        "/api/projects", json={"title": "P", "study_type": "Outcome Study"}
    )
    pid = r.json()["id"]
    r = await client.get(f"/api/projects/{pid}/datasets/ghost/transformations")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_create_rejects_unknown_op_type(client):
    pid, did = await _project_dataset(client)
    # Pydantic Literal returns 422 itself for unknown op_type.
    r = await client.post(
        f"/api/projects/{pid}/datasets/{did}/transformations",
        json={"op_type": "rotate", "op_args": {}},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_transformations_applied_on_analysis_run(client):
    """Filter op makes only 3 of 5 rows visible to the runner — known answer."""
    pid, did = await _project_dataset(client)
    # Pre-set variable types.
    ds_full = (
        await client.get(f"/api/projects/{pid}/datasets/{did}")
    ).json()
    by_name = {v["name"]: v["id"] for v in ds_full["variables"]}
    await client.patch(
        f"/api/projects/{pid}/datasets/{did}/variables/{by_name['y']}",
        json={"user_type": "numeric"},
    )
    await client.patch(
        f"/api/projects/{pid}/datasets/{did}/variables/{by_name['g']}",
        json={"user_type": "nominal"},
    )
    # Add transformation: keep only group "a" rows (3 of 5).
    await client.post(
        f"/api/projects/{pid}/datasets/{did}/transformations",
        json={"op_type": "filter", "op_args": {"column": "g", "op": "==", "value": "a"}},
    )
    # Create analysis: t-test would need 2 groups; use one_way_anova on 1 group?
    # Simpler: ask for a pearson on x vs y after the filter.
    r = await client.post(
        f"/api/projects/{pid}/datasets/{did}/analyses",
        json={
            "question_type": "association",
            "chosen_test": "pearson",
            "variables": {"x": "x", "y": "y"},
        },
    )
    assert r.status_code == 201, r.text
    aid = r.json()["id"]
    r = await client.post(
        f"/api/projects/{pid}/analyses/{aid}/run"
    )
    assert r.status_code == 200, r.text
    # n should reflect the filtered row count.
    summary = r.json()["result"]["summary"]
    assert summary["n"] == 3


@pytest.mark.asyncio
async def test_filter_expr_shape_round_trip_through_analysis_run(client):
    """DEMO-FIX-D HIGH-2 — UI persists ``{expr: "g == 'a'"}``; runner must
    apply it (not 422 with "invalid column name None") end-to-end."""
    pid, did = await _project_dataset(client)
    ds_full = (
        await client.get(f"/api/projects/{pid}/datasets/{did}")
    ).json()
    by_name = {v["name"]: v["id"] for v in ds_full["variables"]}
    await client.patch(
        f"/api/projects/{pid}/datasets/{did}/variables/{by_name['y']}",
        json={"user_type": "numeric"},
    )
    await client.patch(
        f"/api/projects/{pid}/datasets/{did}/variables/{by_name['x']}",
        json={"user_type": "numeric"},
    )

    # Persist the new shape: a single ``expr`` field, no column/op/value.
    r = await client.post(
        f"/api/projects/{pid}/datasets/{did}/transformations",
        json={"op_type": "filter", "op_args": {"expr": "g == 'a'"}},
    )
    assert r.status_code == 201, r.text

    r = await client.post(
        f"/api/projects/{pid}/datasets/{did}/analyses",
        json={
            "question_type": "association",
            "chosen_test": "pearson",
            "variables": {"x": "x", "y": "y"},
        },
    )
    assert r.status_code == 201, r.text
    aid = r.json()["id"]
    r = await client.post(f"/api/projects/{pid}/analyses/{aid}/run")
    assert r.status_code == 200, r.text
    summary = r.json()["result"]["summary"]
    # Filter kept 3 rows where g == 'a'.
    assert summary["n"] == 3
