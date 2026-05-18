"""Phase 8.6 — POST /projects/{pid}/articles/search-pubmed."""
from __future__ import annotations

from pathlib import Path

import pytest
import respx
from httpx import Response

FIXTURES = Path(__file__).parent / "fixtures"
_ESEARCH = (FIXTURES / "pubmed_esearch_sample.xml").read_text(encoding="utf-8")
_EFETCH = (FIXTURES / "pubmed_efetch_sample.xml").read_text(encoding="utf-8")


async def _make_project(client) -> str:
    r = await client.post(
        "/api/projects", json={"title": "P", "study_type": "Outcome Study"}
    )
    return r.json()["id"]


@pytest.mark.asyncio
async def test_search_pubmed_route_returns_results(client):
    pid = await _make_project(client)
    with respx.mock(base_url="https://eutils.ncbi.nlm.nih.gov") as mock:
        mock.get("/entrez/eutils/esearch.fcgi").mock(
            return_value=Response(200, text=_ESEARCH)
        )
        mock.get("/entrez/eutils/efetch.fcgi").mock(
            return_value=Response(200, text=_EFETCH)
        )
        r = await client.post(
            f"/api/projects/{pid}/articles/search-pubmed",
            json={"query": "anterior hip arthroplasty", "retmax": 20},
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body) >= 1
    assert all(item["source"] == "pubmed" for item in body)


@pytest.mark.asyncio
async def test_search_pubmed_route_passes_settings_api_key_to_service(
    client, monkeypatch
):
    pid = await _make_project(client)
    # Inject ncbi_api_key into the active container's settings.
    from research_api.container import get_container

    get_container().settings.ncbi_api_key = "test-key"  # type: ignore[assignment]

    with respx.mock(base_url="https://eutils.ncbi.nlm.nih.gov") as mock:
        esearch_route = mock.get("/entrez/eutils/esearch.fcgi").mock(
            return_value=Response(200, text=_ESEARCH)
        )
        mock.get("/entrez/eutils/efetch.fcgi").mock(
            return_value=Response(200, text=_EFETCH)
        )
        r = await client.post(
            f"/api/projects/{pid}/articles/search-pubmed",
            json={"query": "x", "retmax": 5},
        )
    assert r.status_code == 200
    captured_url = str(esearch_route.calls[0].request.url)
    assert "api_key=test-key" in captured_url


@pytest.mark.asyncio
async def test_search_pubmed_route_empty_query_returns_422_via_pydantic(client):
    pid = await _make_project(client)
    r = await client.post(
        f"/api/projects/{pid}/articles/search-pubmed",
        json={"query": "", "retmax": 5},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_search_pubmed_route_retmax_capped_at_100(client):
    pid = await _make_project(client)
    r = await client.post(
        f"/api/projects/{pid}/articles/search-pubmed",
        json={"query": "x", "retmax": 1000},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_search_pubmed_route_404_on_wrong_user_project(client):
    r = await client.post(
        "/api/projects/does-not-exist/articles/search-pubmed",
        json={"query": "x", "retmax": 5},
    )
    assert r.status_code == 404
