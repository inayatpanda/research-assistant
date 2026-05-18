"""Phase 11 — manuscript snapshot route tests.

Covers list / create / get / diff / delete plus the snapshot-blob
includes ICMJE front-matter rows added in Phase 10.
"""
from __future__ import annotations

import pytest


async def _make_project(client, title: str = "P") -> str:
    r = await client.post(
        "/api/projects",
        json={"title": title, "study_type": "Outcome Study"},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _upsert_section(client, pid: str, name: str, html: str) -> None:
    r = await client.put(
        f"/api/projects/{pid}/sections/{name}",
        json={"section_name": name, "content": html},
    )
    assert r.status_code in (200, 201), r.text


@pytest.mark.asyncio
async def test_create_and_list_snapshot(client) -> None:
    pid = await _make_project(client)
    await _upsert_section(client, pid, "Introduction", "<p>Initial</p>")

    r = await client.post(
        f"/api/projects/{pid}/snapshots",
        json={"label": "v1", "description": "initial draft"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["label"] == "v1"
    assert body["description"] == "initial draft"
    blob = body["full_blob"]
    sections = {s["section_name"]: s["content"] for s in blob["manuscript_sections"]}
    assert sections["Introduction"] == "<p>Initial</p>"

    r = await client.get(f"/api/projects/{pid}/snapshots")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 1
    assert rows[0]["label"] == "v1"
    # List response is the lightweight Summary — full_blob must NOT leak.
    assert "full_blob" not in rows[0]


@pytest.mark.asyncio
async def test_snapshot_label_unique_409(client) -> None:
    pid = await _make_project(client)
    await client.post(f"/api/projects/{pid}/snapshots", json={"label": "v1"})
    r = await client.post(
        f"/api/projects/{pid}/snapshots", json={"label": "v1"}
    )
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_snapshot_captures_frontmatter_authors(client) -> None:
    pid = await _make_project(client)
    r = await client.post(
        f"/api/projects/{pid}/authors",
        json={"full_name": "Jane Doe", "is_corresponding": True},
    )
    assert r.status_code == 201
    r = await client.patch(
        f"/api/projects/{pid}/frontmatter",
        json={"funding_statement": "NIH grant 42"},
    )
    assert r.status_code == 200

    r = await client.post(
        f"/api/projects/{pid}/snapshots", json={"label": "v1"}
    )
    assert r.status_code == 201
    blob = r.json()["full_blob"]
    assert len(blob["authors"]) == 1
    assert blob["authors"][0]["full_name"] == "Jane Doe"
    assert blob["project_frontmatter"]["funding_statement"] == "NIH grant 42"


@pytest.mark.asyncio
async def test_get_snapshot_includes_full_blob(client) -> None:
    pid = await _make_project(client)
    await _upsert_section(client, pid, "Introduction", "<p>Hello</p>")
    sid = (
        await client.post(
            f"/api/projects/{pid}/snapshots", json={"label": "v1"}
        )
    ).json()["id"]
    r = await client.get(f"/api/projects/{pid}/snapshots/{sid}")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == sid
    assert body["full_blob"]["manuscript_sections"][0]["content"] == "<p>Hello</p>"


@pytest.mark.asyncio
async def test_diff_against_current_emits_unified_lines(client) -> None:
    pid = await _make_project(client)
    await _upsert_section(client, pid, "Introduction", "<p>Original</p>")
    sid = (
        await client.post(
            f"/api/projects/{pid}/snapshots", json={"label": "v1"}
        )
    ).json()["id"]
    # Mutate current state.
    await _upsert_section(client, pid, "Introduction", "<p>Revised</p>")

    r = await client.get(f"/api/projects/{pid}/snapshots/{sid}/diff")
    assert r.status_code == 200
    body = r.json()
    assert body["base_snapshot_id"] == sid
    assert body["target_snapshot_id"] is None
    intro = body["sections"]["Introduction"]
    types = [d["type"] for d in intro]
    assert "-" in types  # original deletion
    assert "+" in types  # revised addition


@pytest.mark.asyncio
async def test_diff_between_two_snapshots(client) -> None:
    pid = await _make_project(client)
    await _upsert_section(client, pid, "Introduction", "<p>A</p>")
    s1 = (
        await client.post(
            f"/api/projects/{pid}/snapshots", json={"label": "v1"}
        )
    ).json()["id"]
    await _upsert_section(client, pid, "Introduction", "<p>B</p>")
    s2 = (
        await client.post(
            f"/api/projects/{pid}/snapshots", json={"label": "v2"}
        )
    ).json()["id"]

    r = await client.get(
        f"/api/projects/{pid}/snapshots/{s1}/diff", params={"target": s2}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["base_snapshot_id"] == s1
    assert body["target_snapshot_id"] == s2
    intro = body["sections"]["Introduction"]
    assert any(d["type"] == "-" and "A" in d["line"] for d in intro)
    assert any(d["type"] == "+" and "B" in d["line"] for d in intro)


@pytest.mark.asyncio
async def test_diff_identical_returns_empty_sections(client) -> None:
    pid = await _make_project(client)
    await _upsert_section(client, pid, "Introduction", "<p>Same</p>")
    s1 = (
        await client.post(
            f"/api/projects/{pid}/snapshots", json={"label": "v1"}
        )
    ).json()["id"]
    s2 = (
        await client.post(
            f"/api/projects/{pid}/snapshots", json={"label": "v2"}
        )
    ).json()["id"]
    r = await client.get(
        f"/api/projects/{pid}/snapshots/{s1}/diff", params={"target": s2}
    )
    assert r.status_code == 200
    assert r.json()["sections"] == {}


@pytest.mark.asyncio
async def test_delete_snapshot(client) -> None:
    pid = await _make_project(client)
    sid = (
        await client.post(
            f"/api/projects/{pid}/snapshots", json={"label": "v1"}
        )
    ).json()["id"]
    r = await client.delete(f"/api/projects/{pid}/snapshots/{sid}")
    assert r.status_code == 204
    r = await client.get(f"/api/projects/{pid}/snapshots/{sid}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_snapshot_404_for_unknown_project(client) -> None:
    r = await client.post(
        "/api/projects/nope/snapshots", json={"label": "v1"}
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_diff_404_for_wrong_target(client) -> None:
    pid = await _make_project(client)
    sid = (
        await client.post(
            f"/api/projects/{pid}/snapshots", json={"label": "v1"}
        )
    ).json()["id"]
    r = await client.get(
        f"/api/projects/{pid}/snapshots/{sid}/diff",
        params={"target": "deadbeef"},
    )
    assert r.status_code == 404
