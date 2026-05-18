"""Phase 8.6 — cross-user / cross-project isolation regression for ingest routes.

Every ingest endpoint must:
  1. 404 when the project belongs to a different user.
  2. Refuse to merge / lookup against articles owned by a different user.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import respx
from httpx import Response

from research_api.container import get_container
from research_api.db.models import Article, Highlight, new_id

FIXTURES = Path(__file__).parent / "fixtures"


def _switch_user(user_id: str) -> None:
    get_container().settings.local_user_id = user_id


async def _make_project(client, title: str = "P") -> str:
    r = await client.post(
        "/api/projects",
        json={"title": title, "study_type": "Outcome Study"},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _seed_article(
    *, project_id: str, user_id: str, title: str = "T", doi: str | None = None
) -> str:
    container = get_container()
    async with container.session_factory() as session:
        a = Article(
            id=new_id(),
            user_id=user_id,
            project_id=project_id,
            title=title,
            doi=doi,
            source="upload",
        )
        session.add(a)
        await session.commit()
        await session.refresh(a)
        return a.id


# ── Cross-user 404 on each ingest surface ────────────────────────────────


@pytest.mark.asyncio
async def test_lookup_doi_404_for_other_users_project(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    _switch_user("user-b")
    r = await client.post(
        f"/api/projects/{pid}/articles/lookup-doi",
        json={"doi": "10.1/x"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_search_pubmed_404_for_other_users_project(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    _switch_user("user-b")
    r = await client.post(
        f"/api/projects/{pid}/articles/search-pubmed",
        json={"query": "x", "retmax": 5},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_import_from_metadata_404_for_other_users_project(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    _switch_user("user-b")
    r = await client.post(
        f"/api/projects/{pid}/articles/import-from-metadata",
        json={"items": [{"title": "x", "source": "doi"}]},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_import_from_metadata_rejects_when_pid_belongs_to_another_user(
    client,
):
    _switch_user("user-a")
    pid_a = await _make_project(client)
    _switch_user("user-b")
    pid_b = await _make_project(client)
    # user-b tries to add an article into pid_a (which belongs to user-a)
    r = await client.post(
        f"/api/projects/{pid_a}/articles/import-from-metadata",
        json={"items": [{"title": "x", "source": "ris"}]},
    )
    assert r.status_code == 404

    # Sanity: user-b can still add to their own project
    r2 = await client.post(
        f"/api/projects/{pid_b}/articles/import-from-metadata",
        json={"items": [{"title": "x", "source": "ris"}]},
    )
    assert r2.status_code == 201


@pytest.mark.asyncio
async def test_import_ris_404_for_other_users_project(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    _switch_user("user-b")
    payload = (FIXTURES / "ris_zotero_sample.ris").read_bytes()
    files = {"file": ("x.ris", payload, "application/x-research-info-systems")}
    r = await client.post(
        f"/api/projects/{pid}/articles/import-ris", files=files
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_import_bibtex_404_for_other_users_project(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    _switch_user("user-b")
    payload = (FIXTURES / "bibtex_zotero_sample.bib").read_bytes()
    files = {"file": ("x.bib", payload, "application/x-bibtex")}
    r = await client.post(
        f"/api/projects/{pid}/articles/import-bibtex", files=files
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_get_duplicates_404_for_other_users_project(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    _switch_user("user-b")
    r = await client.get(f"/api/projects/{pid}/articles/duplicates")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_get_duplicates_only_groups_within_owning_user(client):
    # user-a creates two duplicate articles in their project
    _switch_user("user-a")
    pid_a = await _make_project(client)
    a1 = await _seed_article(
        project_id=pid_a, user_id="user-a", title="X", doi="10.1/dup"
    )
    a2 = await _seed_article(
        project_id=pid_a, user_id="user-a", title="X", doi="10.1/dup"
    )
    # user-b also seeds a dup pair in a sibling project — but it must not
    # surface in user-a's duplicates feed.
    _switch_user("user-b")
    pid_b = await _make_project(client)
    await _seed_article(
        project_id=pid_b, user_id="user-b", title="Y", doi="10.2/dup"
    )
    await _seed_article(
        project_id=pid_b, user_id="user-b", title="Y", doi="10.2/dup"
    )
    _switch_user("user-a")
    r = await client.get(f"/api/projects/{pid_a}/articles/duplicates")
    body = r.json()
    assert len(body) == 1
    assert set(body[0]["candidate_ids"]) == {a1, a2}


@pytest.mark.asyncio
async def test_merge_duplicates_rejects_when_keep_owned_by_another_user(client):
    _switch_user("user-a")
    pid_a = await _make_project(client)
    keep_a = await _seed_article(project_id=pid_a, user_id="user-a", title="K")
    drop_a = await _seed_article(project_id=pid_a, user_id="user-a", title="D")
    # user-b tries to merge user-a's articles
    _switch_user("user-b")
    r = await client.post(
        f"/api/projects/{pid_a}/articles/merge-duplicates",
        json={"keep_id": keep_a, "drop_ids": [drop_a]},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_merge_duplicates_rejects_when_drop_owned_by_another_user(
    client,
):
    _switch_user("user-a")
    pid_a = await _make_project(client)
    drop_a = await _seed_article(
        project_id=pid_a, user_id="user-a", title="D"
    )
    _switch_user("user-b")
    pid_b = await _make_project(client)
    keep_b = await _seed_article(
        project_id=pid_b, user_id="user-b", title="K"
    )
    # user-b attempts to merge user-a's drop into their keep
    r = await client.post(
        f"/api/projects/{pid_b}/articles/merge-duplicates",
        json={"keep_id": keep_b, "drop_ids": [drop_a]},
    )
    assert r.status_code == 422
    assert "drop article not found" in r.json()["detail"]


@pytest.mark.asyncio
async def test_merge_duplicates_rejects_when_articles_in_different_projects(
    client,
):
    _switch_user("user-a")
    pid_a1 = await _make_project(client)
    pid_a2 = await _make_project(client)
    keep = await _seed_article(project_id=pid_a1, user_id="user-a", title="K")
    drop = await _seed_article(project_id=pid_a2, user_id="user-a", title="D")
    r = await client.post(
        f"/api/projects/{pid_a1}/articles/merge-duplicates",
        json={"keep_id": keep, "drop_ids": [drop]},
    )
    assert r.status_code == 422
    assert "cross-project" in r.json()["detail"]
