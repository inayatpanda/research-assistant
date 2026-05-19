"""Phase 19 (MP19) — MeSH lookup / suggest / cache routes."""
from __future__ import annotations

import pytest
import respx
from httpx import Response

from research_api.services.ingest.mesh import EFETCH_URL, ESEARCH_URL


_SAMPLE_ESEARCH = """<?xml version="1.0"?>
<eSearchResult>
  <Count>1</Count>
  <IdList><Id>68013313</Id></IdList>
</eSearchResult>
"""

_SAMPLE_FETCH = """<?xml version="1.0"?>
<DescriptorRecordSet>
  <DescriptorRecord>
    <DescriptorUI>D013313</DescriptorUI>
    <DescriptorName><String>Hip Replacement, Total</String></DescriptorName>
    <ConceptList>
      <Concept><ScopeNote>Total hip joint replacement.</ScopeNote></Concept>
    </ConceptList>
    <TreeNumberList><TreeNumber>E04.555.395</TreeNumber></TreeNumberList>
    <ConceptList>
      <Concept><TermList><Term><String>THR</String></Term></TermList></Concept>
    </ConceptList>
  </DescriptorRecord>
</DescriptorRecordSet>
"""


async def _make_project(client) -> str:
    r = await client.post(
        "/api/projects",
        json={"title": "P19", "study_type": "Systematic Review"},
    )
    return r.json()["id"]


@pytest.mark.asyncio
@respx.mock
async def test_search_mesh_returns_hits_and_caches(client):
    pid = await _make_project(client)
    respx.get(ESEARCH_URL).respond(text=_SAMPLE_ESEARCH, status_code=200)
    respx.get(EFETCH_URL).respond(text=_SAMPLE_FETCH, status_code=200)

    r = await client.get(
        f"/api/projects/{pid}/review/mesh/search",
        params={"q": "hip arthroplasty"},
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body["hits"]) == 1
    assert body["hits"][0]["descriptor_ui"] == "D013313"

    # Cache filled
    r2 = await client.get(f"/api/projects/{pid}/review/mesh/cache")
    assert r2.status_code == 200
    assert any(m["descriptor_ui"] == "D013313" for m in r2.json())


@pytest.mark.asyncio
@respx.mock
async def test_search_mesh_no_results_returns_empty(client):
    pid = await _make_project(client)
    respx.get(ESEARCH_URL).respond(
        text='<?xml version="1.0"?><eSearchResult><IdList/></eSearchResult>',
        status_code=200,
    )
    r = await client.get(
        f"/api/projects/{pid}/review/mesh/search",
        params={"q": "xyzxyz"},
    )
    assert r.status_code == 200
    assert r.json()["hits"] == []


@pytest.mark.asyncio
async def test_search_mesh_rejects_missing_q(client):
    pid = await _make_project(client)
    r = await client.get(f"/api/projects/{pid}/review/mesh/search")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_search_mesh_unknown_project_404(client):
    r = await client.get(
        "/api/projects/nonexistent/review/mesh/search",
        params={"q": "hip"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
@respx.mock
async def test_suggest_mesh_uses_review_pico(client):
    pid = await _make_project(client)
    # Seed PICO
    r = await client.patch(
        f"/api/projects/{pid}/reviews",
        json={
            "pico_population": "adults with hip osteoarthritis",
            "pico_intervention": "total hip arthroplasty",
            "pico_comparator": "non-operative care",
            "pico_outcome": "pain",
        },
    )
    assert r.status_code == 200

    respx.get(ESEARCH_URL).respond(text=_SAMPLE_ESEARCH, status_code=200)
    respx.get(EFETCH_URL).respond(text=_SAMPLE_FETCH, status_code=200)

    r = await client.post(f"/api/projects/{pid}/review/mesh/suggest")
    assert r.status_code == 200
    assert len(r.json()["hits"]) == 1


@pytest.mark.asyncio
async def test_create_and_delete_cache_row(client):
    pid = await _make_project(client)
    r = await client.post(
        f"/api/projects/{pid}/review/mesh/cache",
        json={
            "descriptor_ui": "D000001",
            "descriptor_name": "Test Term",
            "tree_numbers": ["A01"],
            "entry_terms": ["alt"],
            "source": "user_added",
        },
    )
    assert r.status_code == 201
    mid = r.json()["id"]

    r = await client.get(f"/api/projects/{pid}/review/mesh/cache")
    assert any(m["id"] == mid for m in r.json())

    r = await client.delete(f"/api/projects/{pid}/review/mesh/cache/{mid}")
    assert r.status_code == 204

    r = await client.get(f"/api/projects/{pid}/review/mesh/cache")
    assert not any(m["id"] == mid for m in r.json())
