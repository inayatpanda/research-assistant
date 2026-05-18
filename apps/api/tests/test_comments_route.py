"""Phase 11 — manuscript margin-comment route tests."""
from __future__ import annotations

import pytest


async def _make_project(client) -> str:
    r = await client.post(
        "/api/projects",
        json={"title": "P", "study_type": "Outcome Study"},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


@pytest.mark.asyncio
async def test_create_and_list_comment(client) -> None:
    pid = await _make_project(client)
    r = await client.post(
        f"/api/projects/{pid}/comments",
        json={
            "section_name": "Introduction",
            "anchor_start": 10,
            "anchor_end": 20,
            "body": "Cite a reference here",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["body"] == "Cite a reference here"
    assert body["resolved"] is False

    r = await client.get(f"/api/projects/{pid}/comments")
    assert r.status_code == 200
    assert len(r.json()) == 1


@pytest.mark.asyncio
async def test_list_filter_by_section_and_resolved(client) -> None:
    pid = await _make_project(client)
    for name in ("Introduction", "Results"):
        r = await client.post(
            f"/api/projects/{pid}/comments",
            json={
                "section_name": name,
                "anchor_start": 0,
                "anchor_end": 1,
                "body": f"note for {name}",
            },
        )
        assert r.status_code == 201
    r = await client.get(
        f"/api/projects/{pid}/comments", params={"section": "Results"}
    )
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 1
    assert rows[0]["section_name"] == "Results"

    r = await client.get(
        f"/api/projects/{pid}/comments", params={"resolved": "false"}
    )
    assert len(r.json()) == 2


@pytest.mark.asyncio
async def test_patch_resolved_flag(client) -> None:
    pid = await _make_project(client)
    cid = (
        await client.post(
            f"/api/projects/{pid}/comments",
            json={
                "section_name": "Introduction",
                "anchor_start": 0,
                "anchor_end": 5,
                "body": "draft",
            },
        )
    ).json()["id"]
    r = await client.patch(
        f"/api/projects/{pid}/comments/{cid}", json={"resolved": True}
    )
    assert r.status_code == 200
    assert r.json()["resolved"] is True
    r = await client.get(
        f"/api/projects/{pid}/comments", params={"resolved": "true"}
    )
    assert len(r.json()) == 1


@pytest.mark.asyncio
async def test_patch_body(client) -> None:
    pid = await _make_project(client)
    cid = (
        await client.post(
            f"/api/projects/{pid}/comments",
            json={
                "section_name": "Introduction",
                "anchor_start": 0,
                "anchor_end": 5,
                "body": "draft",
            },
        )
    ).json()["id"]
    r = await client.patch(
        f"/api/projects/{pid}/comments/{cid}", json={"body": "edited"}
    )
    assert r.status_code == 200
    assert r.json()["body"] == "edited"


@pytest.mark.asyncio
async def test_delete_comment(client) -> None:
    pid = await _make_project(client)
    cid = (
        await client.post(
            f"/api/projects/{pid}/comments",
            json={
                "section_name": "Introduction",
                "anchor_start": 0,
                "anchor_end": 5,
                "body": "note",
            },
        )
    ).json()["id"]
    r = await client.delete(f"/api/projects/{pid}/comments/{cid}")
    assert r.status_code == 204
    r = await client.get(f"/api/projects/{pid}/comments")
    assert r.json() == []


@pytest.mark.asyncio
async def test_anchor_range_validation(client) -> None:
    pid = await _make_project(client)
    r = await client.post(
        f"/api/projects/{pid}/comments",
        json={
            "section_name": "Introduction",
            "anchor_start": 50,
            "anchor_end": 10,
            "body": "bad range",
        },
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_unknown_section_rejected_via_query(client) -> None:
    pid = await _make_project(client)
    r = await client.get(
        f"/api/projects/{pid}/comments", params={"section": "Made-up"}
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_create_unknown_section_422(client) -> None:
    pid = await _make_project(client)
    r = await client.post(
        f"/api/projects/{pid}/comments",
        json={
            "section_name": "Made-up",
            "anchor_start": 0,
            "anchor_end": 5,
            "body": "x",
        },
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_frontmatter_section_allowed(client) -> None:
    pid = await _make_project(client)
    r = await client.post(
        f"/api/projects/{pid}/comments",
        json={
            "section_name": "FrontMatter",
            "anchor_start": 0,
            "anchor_end": 1,
            "body": "Verify ORCID for author 2",
        },
    )
    assert r.status_code == 201
