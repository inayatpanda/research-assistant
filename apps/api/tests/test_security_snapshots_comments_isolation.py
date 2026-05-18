"""Phase 11 security regression — confirm snapshots and comments scope by
user_id + project_id.

Drives the live ASGI app with `local_user_id` swapped between Alice and
Bob to verify cross-tenant reads/writes return 404.
"""
from __future__ import annotations

import pytest

from research_api.container import get_container


def _switch_user(user_id: str) -> None:
    get_container().settings.local_user_id = user_id


async def _make_project(client, title: str = "P") -> str:
    r = await client.post(
        "/api/projects",
        json={"title": title, "study_type": "Outcome Study"},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


# ── Snapshots ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_snapshots_404_for_other_user(client) -> None:
    _switch_user("alice")
    pid = await _make_project(client)
    await client.post(f"/api/projects/{pid}/snapshots", json={"label": "v1"})
    _switch_user("bob")
    r = await client.get(f"/api/projects/{pid}/snapshots")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_get_snapshot_404_for_other_user(client) -> None:
    _switch_user("alice")
    pid = await _make_project(client)
    sid = (
        await client.post(
            f"/api/projects/{pid}/snapshots", json={"label": "v1"}
        )
    ).json()["id"]
    _switch_user("bob")
    r = await client.get(f"/api/projects/{pid}/snapshots/{sid}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_diff_snapshot_404_for_other_user(client) -> None:
    _switch_user("alice")
    pid = await _make_project(client)
    sid = (
        await client.post(
            f"/api/projects/{pid}/snapshots", json={"label": "v1"}
        )
    ).json()["id"]
    _switch_user("bob")
    r = await client.get(f"/api/projects/{pid}/snapshots/{sid}/diff")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_snapshot_404_for_other_user(client) -> None:
    _switch_user("alice")
    pid = await _make_project(client)
    sid = (
        await client.post(
            f"/api/projects/{pid}/snapshots", json={"label": "v1"}
        )
    ).json()["id"]
    _switch_user("bob")
    r = await client.delete(f"/api/projects/{pid}/snapshots/{sid}")
    assert r.status_code == 404
    # Restore alice to confirm the snapshot survives bob's attempt.
    _switch_user("alice")
    r = await client.get(f"/api/projects/{pid}/snapshots/{sid}")
    assert r.status_code == 200


# ── Comments ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_comments_404_for_other_user(client) -> None:
    _switch_user("alice")
    pid = await _make_project(client)
    await client.post(
        f"/api/projects/{pid}/comments",
        json={
            "section_name": "Introduction",
            "anchor_start": 0,
            "anchor_end": 1,
            "body": "alice's note",
        },
    )
    _switch_user("bob")
    r = await client.get(f"/api/projects/{pid}/comments")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_patch_comment_404_for_other_user(client) -> None:
    _switch_user("alice")
    pid = await _make_project(client)
    cid = (
        await client.post(
            f"/api/projects/{pid}/comments",
            json={
                "section_name": "Introduction",
                "anchor_start": 0,
                "anchor_end": 1,
                "body": "alice's note",
            },
        )
    ).json()["id"]
    _switch_user("bob")
    r = await client.patch(
        f"/api/projects/{pid}/comments/{cid}", json={"body": "tampered"}
    )
    assert r.status_code == 404
    _switch_user("alice")
    r = await client.get(f"/api/projects/{pid}/comments")
    assert r.json()[0]["body"] == "alice's note"


@pytest.mark.asyncio
async def test_delete_comment_404_for_other_user(client) -> None:
    _switch_user("alice")
    pid = await _make_project(client)
    cid = (
        await client.post(
            f"/api/projects/{pid}/comments",
            json={
                "section_name": "Introduction",
                "anchor_start": 0,
                "anchor_end": 1,
                "body": "alice's note",
            },
        )
    ).json()["id"]
    _switch_user("bob")
    r = await client.delete(f"/api/projects/{pid}/comments/{cid}")
    assert r.status_code == 404
    _switch_user("alice")
    assert len((await client.get(f"/api/projects/{pid}/comments")).json()) == 1


@pytest.mark.asyncio
async def test_bundle_round_trip_carries_snapshots_and_comments(client) -> None:
    """Round-trip a bundle: a snapshot + comment survives export → import.

    Also doubles as the import-side isolation check: bob imports alice's
    bundle and ends up owning a fresh copy under his own user_id.
    """
    _switch_user("alice")
    pid = await _make_project(client)
    # Tee up content so the snapshot's blob isn't empty.
    await client.put(
        f"/api/projects/{pid}/sections/Introduction",
        json={"section_name": "Introduction", "content": "<p>Original</p>"},
    )
    await client.post(
        f"/api/projects/{pid}/snapshots",
        json={"label": "v1", "description": "first draft"},
    )
    await client.post(
        f"/api/projects/{pid}/comments",
        json={
            "section_name": "Introduction",
            "anchor_start": 0,
            "anchor_end": 5,
            "body": "alice's comment",
        },
    )

    r = await client.post(f"/api/projects/{pid}/export/bundle")
    assert r.status_code == 200
    bundle_bytes = r.content

    _switch_user("bob")
    r = await client.post(
        "/api/projects/import/bundle",
        files={"file": ("bundle.json", bundle_bytes, "application/json")},
    )
    assert r.status_code == 200, r.text
    counts = r.json()["counts"]
    assert counts["manuscript_snapshots"] == 1
    assert counts["manuscript_comments"] == 1
    new_pid = r.json()["project_id"]

    rows = (await client.get(f"/api/projects/{new_pid}/snapshots")).json()
    assert len(rows) == 1
    assert rows[0]["label"] == "v1"
    comments = (await client.get(f"/api/projects/{new_pid}/comments")).json()
    assert len(comments) == 1
    assert comments[0]["body"] == "alice's comment"
