"""Phase 8.7 — Figures route: list, reorder, delete."""
from __future__ import annotations

from pathlib import Path

import pytest

FIX = Path(__file__).parent / "fixtures"


async def _project(client) -> str:
    r = await client.post(
        "/api/projects", json={"title": "P", "study_type": "Outcome Study"}
    )
    return r.json()["id"]


async def _upload(client, pid: str, filename: str = "tiny.png") -> str:
    data = (FIX / filename).read_bytes()
    r = await client.post(
        f"/api/projects/{pid}/figures",
        files={"file": (filename, data, "image/png")},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


@pytest.mark.asyncio
async def test_list_figures_ordered_by_number(client) -> None:
    pid = await _project(client)
    a = await _upload(client, pid)
    b = await _upload(client, pid)
    r = await client.get(f"/api/projects/{pid}/figures")
    assert r.status_code == 200
    rows = r.json()
    assert [x["id"] for x in rows] == [a, b]
    assert [x["figure_number"] for x in rows] == [1, 2]


@pytest.mark.asyncio
async def test_reorder_rewrites_numbers(client) -> None:
    pid = await _project(client)
    a = await _upload(client, pid)
    b = await _upload(client, pid)
    c = await _upload(client, pid)
    r = await client.post(
        f"/api/projects/{pid}/figures/reorder",
        json={"ordered_figure_ids": [c, a, b]},
    )
    assert r.status_code == 200, r.text
    rows = r.json()
    by_id = {x["id"]: x["figure_number"] for x in rows}
    assert by_id[c] == 1 and by_id[a] == 2 and by_id[b] == 3


@pytest.mark.asyncio
async def test_reorder_422_when_ids_mismatch(client) -> None:
    pid = await _project(client)
    a = await _upload(client, pid)
    r = await client.post(
        f"/api/projects/{pid}/figures/reorder",
        json={"ordered_figure_ids": [a, "ghost"]},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_delete_removes_file_from_storage(client) -> None:
    pid = await _project(client)
    fid = await _upload(client, pid)
    r = await client.delete(f"/api/figures/{fid}")
    assert r.status_code == 204
    # After delete, list is empty
    r2 = await client.get(f"/api/projects/{pid}/figures")
    assert r2.json() == []


@pytest.mark.asyncio
async def test_delete_recompacts_numbers(client) -> None:
    pid = await _project(client)
    a = await _upload(client, pid)
    b = await _upload(client, pid)
    c = await _upload(client, pid)
    await client.delete(f"/api/figures/{b}")
    r = await client.get(f"/api/projects/{pid}/figures")
    rows = r.json()
    assert [x["id"] for x in rows] == [a, c]
    assert [x["figure_number"] for x in rows] == [1, 2]


@pytest.mark.asyncio
async def test_delete_404(client) -> None:
    r = await client.delete("/api/figures/notreal")
    assert r.status_code == 404
