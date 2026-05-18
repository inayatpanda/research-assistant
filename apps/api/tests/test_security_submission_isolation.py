"""Phase 12 security regression — confirm cover_letter + reviewer_responses
+ submission package are scoped by user_id + project_id.

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


# ── Cover letter ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_cover_letter_404_for_other_user(client) -> None:
    _switch_user("alice")
    pid = await _make_project(client)
    await client.get(f"/api/projects/{pid}/cover-letter")
    _switch_user("bob")
    r = await client.get(f"/api/projects/{pid}/cover-letter")
    # Bob does not own the project — 404, not the alice row.
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_patch_cover_letter_404_for_other_user(client) -> None:
    _switch_user("alice")
    pid = await _make_project(client)
    await client.get(f"/api/projects/{pid}/cover-letter")
    _switch_user("bob")
    r = await client.patch(
        f"/api/projects/{pid}/cover-letter",
        json={"body_html": "<p>hijack</p>"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_draft_cover_letter_404_for_other_user(client) -> None:
    _switch_user("alice")
    pid = await _make_project(client)
    await client.patch(
        f"/api/projects/{pid}/cover-letter", json={"target_journal": "jbjs"}
    )
    _switch_user("bob")
    r = await client.post(
        f"/api/projects/{pid}/cover-letter/draft", json={}
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_cover_letter_per_project_scope(client) -> None:
    """A cover letter on project A is not visible from project B even for
    the same user."""
    _switch_user("alice")
    a = await _make_project(client, title="A")
    b = await _make_project(client, title="B")
    await client.patch(
        f"/api/projects/{a}/cover-letter",
        json={"body_html": "<p>A-body</p>"},
    )
    r = await client.get(f"/api/projects/{b}/cover-letter")
    assert r.status_code == 200
    assert r.json()["body_html"] == ""  # B starts empty — A's body did NOT leak.


# ── Reviewer responses ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_reviewer_responses_404_for_other_user(client) -> None:
    _switch_user("alice")
    pid = await _make_project(client)
    await client.post(
        f"/api/projects/{pid}/reviewer-responses",
        json={"reviewer_label": "R1", "raw_comments": "Add x"},
    )
    _switch_user("bob")
    r = await client.get(f"/api/projects/{pid}/reviewer-responses")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_create_reviewer_response_404_for_other_user(client) -> None:
    _switch_user("alice")
    pid = await _make_project(client)
    _switch_user("bob")
    r = await client.post(
        f"/api/projects/{pid}/reviewer-responses",
        json={"reviewer_label": "R1", "raw_comments": "evil"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_patch_reviewer_response_404_for_other_user(client) -> None:
    _switch_user("alice")
    pid = await _make_project(client)
    rid = (
        await client.post(
            f"/api/projects/{pid}/reviewer-responses",
            json={"reviewer_label": "R1", "raw_comments": "x"},
        )
    ).json()["id"]
    _switch_user("bob")
    r = await client.patch(
        f"/api/projects/{pid}/reviewer-responses/{rid}",
        json={"reviewer_label": "evil"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_reviewer_response_404_for_other_user(client) -> None:
    _switch_user("alice")
    pid = await _make_project(client)
    rid = (
        await client.post(
            f"/api/projects/{pid}/reviewer-responses",
            json={"reviewer_label": "R1", "raw_comments": "x"},
        )
    ).json()["id"]
    _switch_user("bob")
    r = await client.delete(
        f"/api/projects/{pid}/reviewer-responses/{rid}"
    )
    assert r.status_code == 404
    # Alice's row survives the hostile delete attempt.
    _switch_user("alice")
    listed = await client.get(f"/api/projects/{pid}/reviewer-responses")
    assert any(r["id"] == rid for r in listed.json())


@pytest.mark.asyncio
async def test_reviewer_response_cross_project_returns_404(client) -> None:
    """A reviewer-response created on project A cannot be patched via
    project B's URL even for the same user."""
    _switch_user("alice")
    a = await _make_project(client, title="A")
    b = await _make_project(client, title="B")
    rid = (
        await client.post(
            f"/api/projects/{a}/reviewer-responses",
            json={"reviewer_label": "R1", "raw_comments": "x"},
        )
    ).json()["id"]
    # Same user, wrong project URL.
    r = await client.patch(
        f"/api/projects/{b}/reviewer-responses/{rid}",
        json={"reviewer_label": "evil"},
    )
    assert r.status_code == 404
    # Sanity — the row is still reachable via project A.
    listed = await client.get(f"/api/projects/{a}/reviewer-responses")
    assert any(r["id"] == rid for r in listed.json())


# ── Submission package ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_submission_package_404_for_other_user(client) -> None:
    _switch_user("alice")
    pid = await _make_project(client)
    _switch_user("bob")
    r = await client.post(
        f"/api/projects/{pid}/export/submission-package"
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_submission_package_snapshot_belongs_to_other_user(client) -> None:
    _switch_user("alice")
    pid = await _make_project(client)
    sid = (
        await client.post(
            f"/api/projects/{pid}/snapshots", json={"label": "v1"}
        )
    ).json()["id"]
    _switch_user("bob")
    # Bob doesn't even own the project — should be the project 404.
    r = await client.post(
        f"/api/projects/{pid}/export/submission-package",
        params={"snapshot_id": sid},
    )
    assert r.status_code == 404
