"""Phase 8.6 — services/ingest/crossref.py: DOI → ArticleMetadata.

Tests use ``httpx.MockTransport`` (same pattern as ``tests/test_crossref.py``).
"""
from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from research_api.services.ingest.crossref import lookup_doi_metadata

_FIXTURE = Path(__file__).parent / "fixtures" / "crossref_sample.json"


def _load_sample() -> dict:
    return json.loads(_FIXTURE.read_text(encoding="utf-8"))


def _transport(handler):
    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_lookup_doi_metadata_happy_path():
    sample = _load_sample()

    def handler(request):
        # Crossref base URL hit
        assert "/works/" in str(request.url)
        return httpx.Response(200, json=sample)

    async with httpx.AsyncClient(transport=_transport(handler)) as client:
        meta = await lookup_doi_metadata(
            "10.1056/NEJMoa2110345", http_client=client
        )

    assert meta is not None
    assert meta.title.startswith("Anterior versus Posterior")
    assert meta.authors[0] == "Sarah J. Patel"
    assert meta.journal == "The New England Journal of Medicine"
    assert meta.year == 2023
    assert meta.doi == "10.1056/NEJMoa2110345"
    assert meta.source == "doi"


@pytest.mark.asyncio
async def test_lookup_doi_metadata_extracts_abstract_strips_jats():
    sample = _load_sample()

    def handler(request):
        return httpx.Response(200, json=sample)

    async with httpx.AsyncClient(transport=_transport(handler)) as client:
        meta = await lookup_doi_metadata(
            "10.1056/NEJMoa2110345", http_client=client
        )

    assert meta is not None
    assert meta.abstract is not None
    # JATS tags stripped
    assert "<jats:" not in meta.abstract
    assert "BACKGROUND:" in meta.abstract
    assert "METHODS:" in meta.abstract
    assert "Total hip arthroplasty" in meta.abstract


@pytest.mark.asyncio
async def test_lookup_doi_metadata_returns_none_on_404():
    def handler(request):
        return httpx.Response(404, json={})

    async with httpx.AsyncClient(transport=_transport(handler)) as client:
        assert (
            await lookup_doi_metadata("10.9999/missing.2026", http_client=client)
            is None
        )


@pytest.mark.asyncio
async def test_lookup_doi_metadata_returns_none_on_network_error():
    def handler(request):
        raise httpx.NetworkError("simulated")

    async with httpx.AsyncClient(transport=_transport(handler)) as client:
        assert (
            await lookup_doi_metadata("10.1056/NEJMoa2110345", http_client=client)
            is None
        )


@pytest.mark.asyncio
async def test_lookup_doi_metadata_normalises_doi_prefix():
    sample = _load_sample()

    captured = {}

    def handler(request):
        captured["url"] = str(request.url)
        return httpx.Response(200, json=sample)

    async with httpx.AsyncClient(transport=_transport(handler)) as client:
        meta = await lookup_doi_metadata(
            "https://doi.org/10.1056/NEJMoa2110345", http_client=client
        )

    assert meta is not None
    # The base DOI (no https://doi.org/ prefix) ends up in the URL
    assert "10.1056/NEJMoa2110345" in captured["url"]
    assert "https://doi.org/10.1056" not in captured["url"]


@pytest.mark.asyncio
async def test_lookup_doi_metadata_handles_missing_authors_list_gracefully():
    sample = _load_sample()
    sample["message"].pop("author")

    def handler(request):
        return httpx.Response(200, json=sample)

    async with httpx.AsyncClient(transport=_transport(handler)) as client:
        meta = await lookup_doi_metadata(
            "10.1056/NEJMoa2110345", http_client=client
        )

    assert meta is not None
    assert meta.authors == []


@pytest.mark.asyncio
async def test_lookup_doi_metadata_handles_missing_abstract_gracefully():
    sample = _load_sample()
    sample["message"].pop("abstract")

    def handler(request):
        return httpx.Response(200, json=sample)

    async with httpx.AsyncClient(transport=_transport(handler)) as client:
        meta = await lookup_doi_metadata(
            "10.1056/NEJMoa2110345", http_client=client
        )

    assert meta is not None
    assert meta.abstract is None


@pytest.mark.asyncio
async def test_lookup_doi_metadata_returns_none_for_malformed_doi():
    """No HTTP call when the DOI is malformed."""
    called = {"hit": False}

    def handler(request):
        called["hit"] = True
        return httpx.Response(200, json=_load_sample())

    async with httpx.AsyncClient(transport=_transport(handler)) as client:
        meta = await lookup_doi_metadata("not-a-doi", http_client=client)

    assert meta is None
    assert called["hit"] is False
