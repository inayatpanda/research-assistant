"""Phase 15 (MP15) — Living-review cross-user/project isolation tests."""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from research_api.container import get_container


def _switch_user(user_id: str) -> None:
    get_container().settings.local_user_id = user_id


async def _make_project(client, title: str = "Living SR") -> str:
    r = await client.post(
        "/api/projects",
        json={"title": title, "study_type": "Systematic Review"},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


@dataclass
class _FakeMeta:
    pmid: str
    title: str
    authors: list = None  # type: ignore[assignment]
    journal: str | None = None
    year: int | None = None
    volume: str | None = None
    issue: str | None = None
    pages: str | None = None
    doi: str | None = None
    abstract: str | None = None


def _patch_pubmed(monkeypatch, metas: list[_FakeMeta]) -> None:
    async def fake_search(*_args, **_kwargs):
        return list(metas)

    async def fake_fetch(pmids, *_args, **_kwargs):
        return [m for m in metas if m.pmid in set(pmids)]

    import research_api.routes.living as living_routes
    import research_api.services.ingest.pubmed as pubmed_mod
    import research_api.services.scheduler.runner as runner_mod

    monkeypatch.setattr(pubmed_mod, "search_pubmed", fake_search)
    monkeypatch.setattr(pubmed_mod, "fetch_pmid_metadata", fake_fetch)
    monkeypatch.setattr(runner_mod, "search_pubmed", fake_search)
    monkeypatch.setattr(living_routes, "fetch_pmid_metadata", fake_fetch)


@pytest.mark.asyncio
async def test_get_other_user_returns_404(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    await client.post(
        f"/api/projects/{pid}/review/living",
        json={"pubmed_query": "x", "schedule": "weekly", "enabled": True},
    )
    _switch_user("user-b")
    r = await client.get(f"/api/projects/{pid}/review/living")
    # Project is owned by user-a — user-b sees 404 on the project lookup.
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_patch_other_user_returns_404(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    await client.post(
        f"/api/projects/{pid}/review/living",
        json={"pubmed_query": "x", "schedule": "weekly", "enabled": True},
    )
    _switch_user("user-b")
    r = await client.patch(
        f"/api/projects/{pid}/review/living", json={"schedule": "daily"}
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_other_user_returns_404(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    await client.post(
        f"/api/projects/{pid}/review/living",
        json={"pubmed_query": "x", "schedule": "weekly", "enabled": True},
    )
    _switch_user("user-b")
    r = await client.delete(f"/api/projects/{pid}/review/living")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_run_now_other_user_returns_404(client, monkeypatch):
    _switch_user("user-a")
    pid = await _make_project(client)
    await client.post(
        f"/api/projects/{pid}/review/living",
        json={"pubmed_query": "x", "schedule": "weekly", "enabled": True},
    )
    _patch_pubmed(monkeypatch, [_FakeMeta(pmid="1", title="x")])
    _switch_user("user-b")
    r = await client.post(f"/api/projects/{pid}/review/living/run-now")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_hits_isolated_per_project(client, monkeypatch):
    _switch_user("user-a")
    pid_a = await _make_project(client, "A")
    pid_b = await _make_project(client, "B")
    await client.post(
        f"/api/projects/{pid_a}/review/living",
        json={"pubmed_query": "x", "schedule": "weekly", "enabled": True},
    )
    await client.post(
        f"/api/projects/{pid_b}/review/living",
        json={"pubmed_query": "y", "schedule": "weekly", "enabled": True},
    )
    _patch_pubmed(monkeypatch, [_FakeMeta(pmid="42", title="x")])
    await client.post(f"/api/projects/{pid_a}/review/living/run-now")

    # Project B's hits list must NOT include project A's "42".
    r = await client.get(f"/api/projects/{pid_b}/review/living/hits")
    assert r.status_code == 200
    assert all(h["pmid"] != "42" for h in r.json())


@pytest.mark.asyncio
async def test_hit_decision_other_user_returns_404(client, monkeypatch):
    _switch_user("user-a")
    pid = await _make_project(client)
    await client.post(
        f"/api/projects/{pid}/review/living",
        json={"pubmed_query": "x", "schedule": "weekly", "enabled": True},
    )
    _patch_pubmed(monkeypatch, [_FakeMeta(pmid="9", title="x")])
    await client.post(f"/api/projects/{pid}/review/living/run-now")
    hit = (await client.get(f"/api/projects/{pid}/review/living/hits")).json()[0]

    _switch_user("user-b")
    r = await client.patch(
        f"/api/projects/{pid}/review/living/hits/{hit['id']}",
        json={"decision": "dismissed"},
    )
    assert r.status_code == 404

    r = await client.post(
        f"/api/projects/{pid}/review/living/hits/{hit['id']}/import-as-article",
    )
    assert r.status_code == 404
