"""Phase 10 security regression — prove every front-matter endpoint scopes
the row set by both user_id and project_id.

Same approach as the other test_security_*.py files: drive the live ASGI app
twice with a swapped container.settings.local_user_id.
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


async def _make_author(client, pid: str, full_name: str = "Jane Doe") -> str:
    r = await client.post(
        f"/api/projects/{pid}/authors",
        json={"full_name": full_name},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _make_affiliation(client, pid: str, name: str = "Oxford") -> str:
    r = await client.post(
        f"/api/projects/{pid}/affiliations",
        json={"name": name},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


# ── Authors ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_authors_404_for_other_user(client) -> None:
    _switch_user("alice")
    pid = await _make_project(client)
    await _make_author(client, pid)
    _switch_user("bob")
    r = await client.get(f"/api/projects/{pid}/authors")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_create_author_404_for_other_user(client) -> None:
    _switch_user("alice")
    pid = await _make_project(client)
    _switch_user("bob")
    r = await client.post(
        f"/api/projects/{pid}/authors", json={"full_name": "Jane"}
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_patch_author_404_for_other_user(client) -> None:
    _switch_user("alice")
    pid = await _make_project(client)
    aid = await _make_author(client, pid)
    _switch_user("bob")
    r = await client.patch(f"/api/authors/{aid}", json={"full_name": "Hacked"})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_author_404_for_other_user(client) -> None:
    _switch_user("alice")
    pid = await _make_project(client)
    aid = await _make_author(client, pid)
    _switch_user("bob")
    r = await client.delete(f"/api/authors/{aid}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_reorder_authors_rejects_when_ids_include_other_users_author(client) -> None:
    _switch_user("alice")
    pid_a = await _make_project(client, "A")
    aid_a = await _make_author(client, pid_a)
    _switch_user("bob")
    pid_b = await _make_project(client, "B")
    aid_b = await _make_author(client, pid_b)
    # Bob attempts to smuggle Alice's author id into his reorder call.
    r = await client.post(
        f"/api/projects/{pid_b}/authors/reorder",
        json={"ordered_author_ids": [aid_b, aid_a]},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_set_corresponding_404_for_other_user(client) -> None:
    _switch_user("alice")
    pid = await _make_project(client)
    aid = await _make_author(client, pid)
    _switch_user("bob")
    r = await client.post(f"/api/authors/{aid}/set-corresponding")
    assert r.status_code == 404


# ── Affiliations ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_affiliations_404_for_other_user(client) -> None:
    _switch_user("alice")
    pid = await _make_project(client)
    await _make_affiliation(client, pid)
    _switch_user("bob")
    r = await client.get(f"/api/projects/{pid}/affiliations")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_create_affiliation_404_for_other_user(client) -> None:
    _switch_user("alice")
    pid = await _make_project(client)
    _switch_user("bob")
    r = await client.post(
        f"/api/projects/{pid}/affiliations", json={"name": "Hack U"}
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_patch_affiliation_404_for_other_user(client) -> None:
    _switch_user("alice")
    pid = await _make_project(client)
    fid = await _make_affiliation(client, pid)
    _switch_user("bob")
    r = await client.patch(f"/api/affiliations/{fid}", json={"name": "Hacked"})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_affiliation_404_for_other_user(client) -> None:
    _switch_user("alice")
    pid = await _make_project(client)
    fid = await _make_affiliation(client, pid)
    _switch_user("bob")
    r = await client.delete(f"/api/affiliations/{fid}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_reorder_affiliations_rejects_foreign_ids(client) -> None:
    _switch_user("alice")
    pid_a = await _make_project(client, "A")
    fid_a = await _make_affiliation(client, pid_a)
    _switch_user("bob")
    pid_b = await _make_project(client, "B")
    fid_b = await _make_affiliation(client, pid_b)
    r = await client.post(
        f"/api/projects/{pid_b}/affiliations/reorder",
        json={"ordered_affiliation_ids": [fid_b, fid_a]},
    )
    assert r.status_code == 422


# ── m2m link / unlink ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_link_author_affiliation_404_when_other_user(client) -> None:
    _switch_user("alice")
    pid = await _make_project(client)
    aid = await _make_author(client, pid)
    fid = await _make_affiliation(client, pid)
    _switch_user("bob")
    r = await client.post(f"/api/authors/{aid}/affiliations/{fid}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_link_rejects_cross_project_via_route(client) -> None:
    _switch_user("alice")
    pid_a = await _make_project(client, "A")
    aid = await _make_author(client, pid_a)
    pid_b = await _make_project(client, "B")
    fid_b = await _make_affiliation(client, pid_b)
    r = await client.post(f"/api/authors/{aid}/affiliations/{fid_b}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_unlink_author_affiliation_404_when_other_user(client) -> None:
    _switch_user("alice")
    pid = await _make_project(client)
    aid = await _make_author(client, pid)
    fid = await _make_affiliation(client, pid)
    link_ok = await client.post(f"/api/authors/{aid}/affiliations/{fid}")
    assert link_ok.status_code == 200
    _switch_user("bob")
    r = await client.delete(f"/api/authors/{aid}/affiliations/{fid}")
    assert r.status_code == 404


# ── Contributions ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_set_contribution_404_for_other_user(client) -> None:
    _switch_user("alice")
    pid = await _make_project(client)
    aid = await _make_author(client, pid)
    _switch_user("bob")
    r = await client.post(
        f"/api/authors/{aid}/contributions",
        json={"role": "Conceptualization"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_clear_contribution_404_for_other_user(client) -> None:
    _switch_user("alice")
    pid = await _make_project(client)
    aid = await _make_author(client, pid)
    set_ok = await client.post(
        f"/api/authors/{aid}/contributions",
        json={"role": "Methodology"},
    )
    assert set_ok.status_code == 201
    _switch_user("bob")
    r = await client.delete(f"/api/authors/{aid}/contributions/Methodology")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_list_contributions_404_for_other_user(client) -> None:
    _switch_user("alice")
    pid = await _make_project(client)
    aid = await _make_author(client, pid)
    _switch_user("bob")
    r = await client.get(f"/api/authors/{aid}/contributions")
    assert r.status_code == 404


# ── Frontmatter ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_frontmatter_404_for_other_user(client) -> None:
    _switch_user("alice")
    pid = await _make_project(client)
    _switch_user("bob")
    r = await client.get(f"/api/projects/{pid}/frontmatter")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_patch_frontmatter_404_for_other_user(client) -> None:
    _switch_user("alice")
    pid = await _make_project(client)
    _switch_user("bob")
    r = await client.patch(
        f"/api/projects/{pid}/frontmatter",
        json={"funding_statement": "leaked"},
    )
    assert r.status_code == 404
