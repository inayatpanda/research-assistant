"""Phase 4.6 — Cross-user / cross-project isolation regression for the
AI peer-review module. Every endpoint must 404 when invoked by a user
who does not own the row.
"""
from __future__ import annotations

import pytest

from research_api.container import get_container


def _switch(user_id: str) -> None:
    get_container().settings.local_user_id = user_id


async def _make_project(client, title: str) -> str:
    r = await client.post(
        "/api/projects",
        json={"title": title, "study_type": "Randomised Controlled Trial"},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _make_peer_review(client, pid: str) -> dict:
    # Seed minimal manuscript content so the route's text-length check
    # passes.
    long_body = (
        "Background: study assesses a widget. "
        "Methods: 80 patients randomised to widget or sham. "
        "Results: widget arm improved by 5.3 points (p=0.002). "
        "Discussion: results extend prior data. "
    ) * 2
    for name in (
        "Abstract",
        "Introduction",
        "Methodology",
        "Results",
        "Discussion",
    ):
        sec = await client.put(
            f"/api/projects/{pid}/sections/{name}",
            json={"section_name": name, "content": long_body},
        )
        assert sec.status_code == 200, sec.text
    r = await client.post(f"/api/projects/{pid}/peer-reviews/manuscript")
    assert r.status_code == 201, r.text
    return r.json()


@pytest.mark.asyncio
async def test_user_b_cannot_list_user_a_peer_reviews(client) -> None:
    _switch("user-a")
    pa = await _make_project(client, "A")
    await _make_peer_review(client, pa)
    _switch("user-b")
    r = await client.get(f"/api/projects/{pa}/peer-reviews")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_user_b_cannot_get_user_a_peer_review(client) -> None:
    _switch("user-a")
    pa = await _make_project(client, "A")
    row = await _make_peer_review(client, pa)
    _switch("user-b")
    r = await client.get(f"/api/projects/{pa}/peer-reviews/{row['id']}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_user_b_cannot_create_peer_review_on_user_a_project(client) -> None:
    _switch("user-a")
    pa = await _make_project(client, "A")
    _switch("user-b")
    r = await client.post(f"/api/projects/{pa}/peer-reviews/manuscript")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_user_b_cannot_delete_user_a_peer_review(client) -> None:
    _switch("user-a")
    pa = await _make_project(client, "A")
    row = await _make_peer_review(client, pa)
    _switch("user-b")
    r = await client.delete(f"/api/projects/{pa}/peer-reviews/{row['id']}")
    assert r.status_code == 404
    # Verify row still exists for user A.
    _switch("user-a")
    g = await client.get(f"/api/projects/{pa}/peer-reviews/{row['id']}")
    assert g.status_code == 200


@pytest.mark.asyncio
async def test_peer_review_under_wrong_project_id_returns_404(client) -> None:
    _switch("user-a")
    pa = await _make_project(client, "A")
    pb = await _make_project(client, "B")
    row = await _make_peer_review(client, pa)
    # Looking up project A's review via project B should 404.
    r = await client.get(f"/api/projects/{pb}/peer-reviews/{row['id']}")
    assert r.status_code == 404
    e = await client.post(
        f"/api/projects/{pb}/peer-reviews/{row['id']}/export?format=pdf"
    )
    assert e.status_code == 404
