"""MP16 — Cross-user / cross-project isolation regression for the new
citation-import endpoints and the figure renumber route.
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


# ─── import-from-text ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_import_from_text_404_for_other_users_project(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    _switch_user("user-b")
    r = await client.post(
        f"/api/projects/{pid}/articles/import-from-text",
        json={"text": "1. Doe J. Title. doi:10.1234/x"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_import_from_text_404_for_unknown_project(client):
    _switch_user("user-a")
    r = await client.post(
        "/api/projects/does-not-exist/articles/import-from-text",
        json={"text": "1. X."},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_import_from_text_works_for_own_project(client):
    """Sanity-check the positive control so the negative tests above are
    meaningful (i.e. the route is reachable for the owning user)."""
    _switch_user("user-a")
    pid = await _make_project(client)
    r = await client.post(
        f"/api/projects/{pid}/articles/import-from-text",
        json={"text": "1. Doe J. Title.", "fuzzy_title_lookup": False},
    )
    assert r.status_code == 200, r.text


# ─── figures/renumber ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_renumber_figures_404_for_other_users_project(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    _switch_user("user-b")
    r = await client.post(f"/api/projects/{pid}/figures/renumber")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_renumber_figures_404_for_unknown_project(client):
    _switch_user("user-a")
    r = await client.post("/api/projects/does-not-exist/figures/renumber")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_renumber_figures_empty_project_returns_empty_list(client):
    """Positive control — owning user with no figures returns []."""
    _switch_user("user-a")
    pid = await _make_project(client)
    r = await client.post(f"/api/projects/{pid}/figures/renumber")
    assert r.status_code == 200, r.text
    assert r.json() == []
