"""Phase 13 (MP13) — Cross-dataset route tests."""
from __future__ import annotations

import pytest

CSV_A = b"id,x\n1,10\n2,20\n3,30\n"
CSV_B = b"id,y\n2,200\n3,300\n4,400\n"
CSV_C = b"id,x\n5,50\n6,60\n"


async def _project(client) -> str:
    r = await client.post(
        "/api/projects", json={"title": "P", "study_type": "Outcome Study"}
    )
    return r.json()["id"]


async def _upload(client, pid: str, name: str, body: bytes) -> str:
    r = await client.post(
        f"/api/projects/{pid}/datasets",
        files={"file": (name, body, "text/csv")},
    )
    return r.json()["id"]


@pytest.mark.asyncio
async def test_merge_inner_creates_new_dataset(client):
    pid = await _project(client)
    a = await _upload(client, pid, "a.csv", CSV_A)
    b = await _upload(client, pid, "b.csv", CSV_B)
    r = await client.post(
        f"/api/projects/{pid}/datasets/cross-op",
        json={
            "op": "merge",
            "source_dataset_ids": [a, b],
            "args": {"on": ["id"], "how": "inner"},
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["n_rows"] == 2
    assert body["n_columns"] == 3  # id, x, y
    assert body["source_dataset_ids"] == [a, b]


@pytest.mark.asyncio
async def test_append_combines_rows(client):
    pid = await _project(client)
    a = await _upload(client, pid, "a.csv", CSV_A)
    c = await _upload(client, pid, "c.csv", CSV_C)
    r = await client.post(
        f"/api/projects/{pid}/datasets/cross-op",
        json={"op": "append", "source_dataset_ids": [a, c]},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["n_rows"] == 5


@pytest.mark.asyncio
async def test_merge_with_wrong_source_count_422(client):
    pid = await _project(client)
    a = await _upload(client, pid, "a.csv", CSV_A)
    r = await client.post(
        f"/api/projects/{pid}/datasets/cross-op",
        json={
            "op": "merge",
            "source_dataset_ids": [a],
            "args": {"on": ["id"]},
        },
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_join_creates_dataset_with_derived_list(client):
    pid = await _project(client)
    a = await _upload(client, pid, "a.csv", CSV_A)
    b = await _upload(client, pid, "b.csv", CSV_B)
    r = await client.post(
        f"/api/projects/{pid}/datasets/cross-op",
        json={
            "op": "join",
            "source_dataset_ids": [a, b],
            "args": {"on": "id", "how": "left"},
        },
    )
    assert r.status_code == 201, r.text
    new_id = r.json()["dataset_id"]
    # Pull the new dataset and check its derived_from_dataset_ids round-trip.
    r = await client.get(f"/api/projects/{pid}/datasets/{new_id}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("derived_from_dataset_ids") == [a, b]


@pytest.mark.asyncio
async def test_missing_source_dataset_404(client):
    pid = await _project(client)
    a = await _upload(client, pid, "a.csv", CSV_A)
    r = await client.post(
        f"/api/projects/{pid}/datasets/cross-op",
        json={
            "op": "merge",
            "source_dataset_ids": [a, "ghost"],
            "args": {"on": ["id"]},
        },
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_unknown_project_404(client):
    r = await client.post(
        "/api/projects/ghost/datasets/cross-op",
        json={"op": "append", "source_dataset_ids": ["a", "b"]},
    )
    assert r.status_code == 404
