"""Phase 8.6 — POST /projects/{pid}/articles/lookup-doi."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import respx
from httpx import Response

FIXTURES = Path(__file__).parent / "fixtures"


def _crossref_sample() -> dict:
    return json.loads((FIXTURES / "crossref_sample.json").read_text())


async def _make_project(client) -> str:
    r = await client.post(
        "/api/projects", json={"title": "P", "study_type": "Outcome Study"}
    )
    return r.json()["id"]


@pytest.mark.asyncio
async def test_lookup_doi_route_returns_metadata(client):
    pid = await _make_project(client)
    with respx.mock(base_url="https://api.crossref.org") as mock:
        mock.get("/works/10.1056/NEJMoa2110345").mock(
            return_value=Response(200, json=_crossref_sample())
        )
        r = await client.post(
            f"/api/projects/{pid}/articles/lookup-doi",
            json={"doi": "10.1056/NEJMoa2110345"},
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["title"].startswith("Anterior versus Posterior")
    assert body["source"] == "doi"
    assert body["doi"] == "10.1056/NEJMoa2110345"


@pytest.mark.asyncio
async def test_lookup_doi_route_404_on_missing_doi(client):
    pid = await _make_project(client)
    with respx.mock(base_url="https://api.crossref.org") as mock:
        mock.get("/works/10.9999/missing").mock(return_value=Response(404))
        r = await client.post(
            f"/api/projects/{pid}/articles/lookup-doi",
            json={"doi": "10.9999/missing"},
        )
    assert r.status_code == 404
    assert "Crossref" in r.json()["detail"]


@pytest.mark.asyncio
async def test_lookup_doi_route_404_on_wrong_user_project(client):
    # No project created; the project_id is unknown
    r = await client.post(
        "/api/projects/does-not-exist/articles/lookup-doi",
        json={"doi": "10.1234/x"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_lookup_doi_route_normalises_https_prefixed_doi(client):
    pid = await _make_project(client)
    with respx.mock(base_url="https://api.crossref.org") as mock:
        route = mock.get("/works/10.1056/NEJMoa2110345").mock(
            return_value=Response(200, json=_crossref_sample())
        )
        r = await client.post(
            f"/api/projects/{pid}/articles/lookup-doi",
            json={"doi": "https://doi.org/10.1056/NEJMoa2110345"},
        )
    assert r.status_code == 200
    assert route.called


@pytest.mark.asyncio
async def test_lookup_doi_route_422_on_empty_body(client):
    pid = await _make_project(client)
    r = await client.post(
        f"/api/projects/{pid}/articles/lookup-doi", json={"doi": ""}
    )
    assert r.status_code == 422
