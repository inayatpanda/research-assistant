"""Phase 15 (MP15) — Living systematic review routes (CRUD + run-now + import)."""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from research_api.container import get_container


def _switch_user(user_id: str) -> None:
    get_container().settings.local_user_id = user_id


async def _make_project(client, title: str = "Living SR") -> str:
    r = await client.post(
        "/api/projects", json={"title": title, "study_type": "Systematic Review"}
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
    """Stub both search_pubmed and fetch_pmid_metadata at every import site."""

    async def fake_search(*_args, **_kwargs):
        return list(metas)

    async def fake_fetch(pmids, *_args, **_kwargs):
        return [m for m in metas if m.pmid in set(pmids)]

    import research_api.services.ingest.pubmed as pubmed_mod
    import research_api.services.scheduler.runner as runner_mod
    import research_api.routes.living as living_routes

    monkeypatch.setattr(pubmed_mod, "search_pubmed", fake_search)
    monkeypatch.setattr(pubmed_mod, "fetch_pmid_metadata", fake_fetch)
    monkeypatch.setattr(runner_mod, "search_pubmed", fake_search)
    monkeypatch.setattr(living_routes, "fetch_pmid_metadata", fake_fetch)


@pytest.mark.asyncio
async def test_get_404_before_any_upsert(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    r = await client.get(f"/api/projects/{pid}/review/living")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_upsert_creates_then_patch_updates(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    r = await client.post(
        f"/api/projects/{pid}/review/living",
        json={"pubmed_query": "aspirin AND stroke", "schedule": "weekly", "enabled": True},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["pubmed_query"] == "aspirin AND stroke"
    assert body["schedule"] == "weekly"
    assert body["enabled"] is True

    # GET reflects the upsert.
    r = await client.get(f"/api/projects/{pid}/review/living")
    assert r.status_code == 200
    assert r.json()["pubmed_query"] == "aspirin AND stroke"

    # PATCH narrows schedule + disables.
    r = await client.patch(
        f"/api/projects/{pid}/review/living",
        json={"schedule": "daily", "enabled": False},
    )
    assert r.status_code == 200, r.text
    assert r.json()["schedule"] == "daily"
    assert r.json()["enabled"] is False


@pytest.mark.asyncio
async def test_delete_removes_job(client):
    _switch_user("user-a")
    pid = await _make_project(client)
    await client.post(
        f"/api/projects/{pid}/review/living",
        json={"pubmed_query": "x", "schedule": "weekly", "enabled": True},
    )
    r = await client.delete(f"/api/projects/{pid}/review/living")
    assert r.status_code == 204
    # Subsequent GET is 404.
    assert (await client.get(f"/api/projects/{pid}/review/living")).status_code == 404


@pytest.mark.asyncio
async def test_run_now_inserts_hits(client, monkeypatch):
    _switch_user("user-a")
    pid = await _make_project(client)
    await client.post(
        f"/api/projects/{pid}/review/living",
        json={"pubmed_query": "x", "schedule": "weekly", "enabled": True},
    )
    _patch_pubmed(
        monkeypatch,
        [
            _FakeMeta(pmid="100", title="Aspirin study A"),
            _FakeMeta(pmid="200", title="Aspirin study B"),
        ],
    )

    r = await client.post(f"/api/projects/{pid}/review/living/run-now")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["new_hits"] == 2
    assert body["total_fetched"] == 2

    # Listing returns both new hits.
    r = await client.get(f"/api/projects/{pid}/review/living/hits?decision=new")
    assert r.status_code == 200
    assert len(r.json()) == 2

    # Second run with same fixture → no new hits (everything's been seen).
    r = await client.post(f"/api/projects/{pid}/review/living/run-now")
    assert r.json()["new_hits"] == 0


@pytest.mark.asyncio
async def test_hit_decision_flow_dismiss_then_accept(client, monkeypatch):
    _switch_user("user-a")
    pid = await _make_project(client)
    await client.post(
        f"/api/projects/{pid}/review/living",
        json={"pubmed_query": "x", "schedule": "weekly", "enabled": True},
    )
    _patch_pubmed(
        monkeypatch,
        [
            _FakeMeta(pmid="100", title="A"),
            _FakeMeta(pmid="200", title="B"),
        ],
    )
    await client.post(f"/api/projects/{pid}/review/living/run-now")
    hits = (await client.get(f"/api/projects/{pid}/review/living/hits")).json()
    hit_a, hit_b = hits[0], hits[1]

    r = await client.patch(
        f"/api/projects/{pid}/review/living/hits/{hit_a['id']}",
        json={"decision": "dismissed"},
    )
    assert r.status_code == 200
    assert r.json()["decision"] == "dismissed"

    r = await client.patch(
        f"/api/projects/{pid}/review/living/hits/{hit_b['id']}",
        json={"decision": "accepted"},
    )
    assert r.status_code == 200
    assert r.json()["decision"] == "accepted"

    # Filter by decision works.
    listed = (
        await client.get(f"/api/projects/{pid}/review/living/hits?decision=dismissed")
    ).json()
    assert len(listed) == 1
    assert listed[0]["pmid"] == hit_a["pmid"]


@pytest.mark.asyncio
async def test_import_accepted_hit_as_article(client, monkeypatch):
    _switch_user("user-a")
    pid = await _make_project(client)
    await client.post(
        f"/api/projects/{pid}/review/living",
        json={"pubmed_query": "x", "schedule": "weekly", "enabled": True},
    )
    fake_meta = _FakeMeta(
        pmid="555",
        title="Aspirin lowers stroke risk",
        authors=["A B", "C D"],
        journal="JAMA",
        year=2024,
        doi="10.1000/x.555",
        abstract="…",
    )
    _patch_pubmed(monkeypatch, [fake_meta])
    await client.post(f"/api/projects/{pid}/review/living/run-now")
    hits = (await client.get(f"/api/projects/{pid}/review/living/hits")).json()
    hit_id = hits[0]["id"]

    # Must be accepted first.
    r = await client.post(
        f"/api/projects/{pid}/review/living/hits/{hit_id}/import-as-article",
    )
    assert r.status_code == 422

    await client.patch(
        f"/api/projects/{pid}/review/living/hits/{hit_id}",
        json={"decision": "accepted"},
    )
    r = await client.post(
        f"/api/projects/{pid}/review/living/hits/{hit_id}/import-as-article",
    )
    assert r.status_code == 200, r.text
    article = r.json()
    assert article["title"] == "Aspirin lowers stroke risk"
    assert article["pmid"] == "555"
    assert article["source"] == "pubmed"
    assert article["doi"] == "10.1000/x.555"

    # The Article should now appear in the project's articles list.
    r = await client.get(f"/api/projects/{pid}/articles")
    assert any(a["pmid"] == "555" for a in r.json())


@pytest.mark.asyncio
async def test_get_for_unknown_project_returns_404(client):
    _switch_user("user-a")
    r = await client.get("/api/projects/nope/review/living")
    assert r.status_code == 404
