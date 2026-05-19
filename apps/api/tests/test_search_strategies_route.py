"""Phase 19 (MP19) — search-strategy CRUD + cross-DB translation."""
from __future__ import annotations

import pytest


async def _make_project(client) -> str:
    r = await client.post(
        "/api/projects",
        json={"title": "P19 SS", "study_type": "Systematic Review"},
    )
    return r.json()["id"]


def _strategy_payload(**overrides):
    return {
        "name": "Initial PubMed",
        "database": "PubMed",
        "query_text": '"hip arthroplasty"[MeSH Terms] AND "anesthesia"[MeSH Terms]',
        "mesh_term_ids": [],
        **overrides,
    }


@pytest.mark.asyncio
async def test_create_and_list_strategy(client):
    pid = await _make_project(client)
    r = await client.post(
        f"/api/projects/{pid}/review/search-strategies",
        json=_strategy_payload(),
    )
    assert r.status_code == 201
    sid = r.json()["id"]

    r = await client.get(f"/api/projects/{pid}/review/search-strategies")
    assert r.status_code == 200
    assert any(s["id"] == sid for s in r.json())


@pytest.mark.asyncio
async def test_translate_to_embase_persist_creates_child_strategy(client):
    pid = await _make_project(client)
    r = await client.post(
        f"/api/projects/{pid}/review/search-strategies",
        json=_strategy_payload(),
    )
    src_id = r.json()["id"]

    r = await client.post(
        f"/api/projects/{pid}/review/search-strategies/{src_id}/translate",
        params={"to": "embase", "persist": "true"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["target"] == "embase"
    assert "'hip arthroplasty'/de" in body["translated_query"]

    # Persisted child
    r = await client.get(f"/api/projects/{pid}/review/search-strategies")
    children = [
        s for s in r.json() if s.get("translated_from_id") == src_id
    ]
    assert len(children) == 1
    assert children[0]["database"] == "Embase"


@pytest.mark.asyncio
async def test_translate_to_cochrane_returns_warnings_when_present(client):
    pid = await _make_project(client)
    r = await client.post(
        f"/api/projects/{pid}/review/search-strategies",
        json=_strategy_payload(query_text='"hip"[MeSH] AND "tooth"[lang]'),
    )
    sid = r.json()["id"]

    r = await client.post(
        f"/api/projects/{pid}/review/search-strategies/{sid}/translate",
        params={"to": "cochrane"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["target"] == "cochrane"
    # [lang] is dropped with warning
    assert any("lang" in w for w in body["warnings"])


@pytest.mark.asyncio
async def test_update_strategy_changes_fields(client):
    pid = await _make_project(client)
    r = await client.post(
        f"/api/projects/{pid}/review/search-strategies",
        json=_strategy_payload(),
    )
    sid = r.json()["id"]

    r = await client.patch(
        f"/api/projects/{pid}/review/search-strategies/{sid}",
        json={"name": "Renamed"},
    )
    assert r.status_code == 200
    assert r.json()["name"] == "Renamed"


@pytest.mark.asyncio
async def test_locked_strategy_rejects_query_edit(client):
    pid = await _make_project(client)
    r = await client.post(
        f"/api/projects/{pid}/review/search-strategies",
        json=_strategy_payload(is_locked=True),
    )
    sid = r.json()["id"]
    r = await client.patch(
        f"/api/projects/{pid}/review/search-strategies/{sid}",
        json={"query_text": "new"},
    )
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_delete_strategy(client):
    pid = await _make_project(client)
    r = await client.post(
        f"/api/projects/{pid}/review/search-strategies",
        json=_strategy_payload(),
    )
    sid = r.json()["id"]
    r = await client.delete(f"/api/projects/{pid}/review/search-strategies/{sid}")
    assert r.status_code == 204
    r = await client.get(f"/api/projects/{pid}/review/search-strategies")
    assert not any(s["id"] == sid for s in r.json())


@pytest.mark.asyncio
async def test_create_with_unknown_translated_from_id_rejected(client):
    pid = await _make_project(client)
    r = await client.post(
        f"/api/projects/{pid}/review/search-strategies",
        json=_strategy_payload(translated_from_id="ffffffff"),
    )
    assert r.status_code == 422
