"""Phase 8.6 — POST /projects/{pid}/articles/import-from-metadata."""
from __future__ import annotations

import pytest


async def _make_project(client) -> str:
    r = await client.post(
        "/api/projects", json={"title": "P", "study_type": "Outcome Study"}
    )
    return r.json()["id"]


def _item(**overrides) -> dict:
    base = {
        "title": "Anterior approach in THA",
        "authors": ["John Doe"],
        "journal": "Test J",
        "year": 2023,
        "source": "doi",
    }
    base.update(overrides)
    return base


@pytest.mark.asyncio
async def test_import_from_metadata_creates_rows_with_correct_source(client):
    pid = await _make_project(client)
    r = await client.post(
        f"/api/projects/{pid}/articles/import-from-metadata",
        json={
            "items": [
                _item(doi="10.1/a", source="doi"),
                _item(title="Posterior approach", source="ris"),
            ]
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert len(body["created"]) == 2
    sources = sorted(a["source"] for a in body["created"])
    assert sources == ["doi", "ris"]
    assert body["skipped_duplicates"] == []


@pytest.mark.asyncio
async def test_import_from_metadata_skips_existing_doi(client):
    pid = await _make_project(client)
    await client.post(
        f"/api/projects/{pid}/articles/import-from-metadata",
        json={"items": [_item(doi="10.1/a")]},
    )
    r = await client.post(
        f"/api/projects/{pid}/articles/import-from-metadata",
        json={"items": [_item(doi="10.1/a", source="ris")]},
    )
    assert r.status_code == 201
    body = r.json()
    assert len(body["created"]) == 0
    assert len(body["skipped_duplicates"]) == 1
    assert body["skipped_duplicates"][0]["doi"] == "10.1/a"


@pytest.mark.asyncio
async def test_import_from_metadata_skips_existing_pmid(client):
    pid = await _make_project(client)
    await client.post(
        f"/api/projects/{pid}/articles/import-from-metadata",
        json={"items": [_item(pmid="12345", source="pubmed")]},
    )
    r = await client.post(
        f"/api/projects/{pid}/articles/import-from-metadata",
        json={"items": [_item(pmid="12345", source="pubmed")]},
    )
    body = r.json()
    assert len(body["created"]) == 0
    assert len(body["skipped_duplicates"]) == 1


@pytest.mark.asyncio
async def test_import_from_metadata_returns_fuzzy_duplicate_groups(client):
    pid = await _make_project(client)
    r = await client.post(
        f"/api/projects/{pid}/articles/import-from-metadata",
        json={
            "items": [
                _item(
                    title="Anterior vs Posterior in Total Hip Arthroplasty",
                    year=2023,
                    source="ris",
                ),
                _item(
                    title="Anterior vs. posterior in total hip arthroplasty",
                    year=2023,
                    source="bibtex",
                ),
            ]
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert len(body["created"]) == 2
    assert len(body["duplicate_groups"]) >= 1
    grp = body["duplicate_groups"][0]
    assert grp["reason"] == "title_fuzzy"
    assert grp["score"] >= 0.92


@pytest.mark.asyncio
async def test_import_from_metadata_404_on_other_user_project(client):
    r = await client.post(
        "/api/projects/missing/articles/import-from-metadata",
        json={"items": [_item()]},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_import_from_metadata_empty_items_returns_422(client):
    pid = await _make_project(client)
    r = await client.post(
        f"/api/projects/{pid}/articles/import-from-metadata",
        json={"items": []},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_import_from_metadata_persists_abstract_and_pmid(client):
    pid = await _make_project(client)
    r = await client.post(
        f"/api/projects/{pid}/articles/import-from-metadata",
        json={
            "items": [
                _item(
                    title="X",
                    pmid="999",
                    abstract="Sample abstract content",
                    source="pubmed",
                )
            ]
        },
    )
    assert r.status_code == 201
    [created] = r.json()["created"]
    assert created["pmid"] == "999"
    assert created["abstract"] == "Sample abstract content"
