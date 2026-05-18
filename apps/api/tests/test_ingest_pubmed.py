"""Phase 8.6 — services/ingest/pubmed.py: esearch + efetch."""
from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from research_api.services.ingest.pubmed import (
    EFETCH_URL,
    ESEARCH_URL,
    fetch_pmid_metadata,
    search_pubmed,
)

_FIXTURES = Path(__file__).parent / "fixtures"
_ESEARCH = (_FIXTURES / "pubmed_esearch_sample.xml").read_text(encoding="utf-8")
_EFETCH = (_FIXTURES / "pubmed_efetch_sample.xml").read_text(encoding="utf-8")

_EMPTY_ESEARCH = (
    '<?xml version="1.0"?>\n'
    "<eSearchResult><Count>0</Count><RetMax>0</RetMax><RetStart>0</RetStart>"
    "<IdList/></eSearchResult>"
)


def _routed(handlers: dict[str, httpx.Response]):
    """Route by URL path component (esearch.fcgi or efetch.fcgi) to a canned response."""

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        for needle, response in handlers.items():
            if needle in path:
                return response
        raise AssertionError(f"unexpected URL: {request.url}")

    return httpx.MockTransport(handler)


def _is_esearch(request: httpx.Request) -> bool:
    return "esearch.fcgi" in request.url.path


def _is_efetch(request: httpx.Request) -> bool:
    return "efetch.fcgi" in request.url.path


@pytest.mark.asyncio
async def test_search_pubmed_happy_path():
    transport = _routed(
        {
            "esearch.fcgi": httpx.Response(200, text=_ESEARCH),
            "efetch.fcgi": httpx.Response(200, text=_EFETCH),
        }
    )
    async with httpx.AsyncClient(transport=transport) as client:
        results = await search_pubmed(
            "anterior approach total hip arthroplasty", http_client=client
        )

    assert len(results) >= 1
    first = next(r for r in results if r.pmid == "37251234")
    assert first.title.startswith("Anterior versus posterior")
    assert first.authors == ["Wei Chen", "Linh Nguyen"]  # collective skipped
    assert first.journal == "JAMA"
    assert first.year == 2023
    assert first.volume == "329"
    assert first.issue == "21"
    assert first.pages == "1843-1852"
    assert first.doi == "10.1001/jama.2023.7770"
    assert first.source == "pubmed"
    assert "BACKGROUND" in (first.abstract or "")
    assert "METHODS" in (first.abstract or "")
    assert "RESULTS" in (first.abstract or "")


@pytest.mark.asyncio
async def test_search_pubmed_empty_query_returns_empty():
    transport = _routed({})
    async with httpx.AsyncClient(transport=transport) as client:
        assert await search_pubmed("", http_client=client) == []
        assert await search_pubmed("   ", http_client=client) == []


@pytest.mark.asyncio
async def test_search_pubmed_zero_results_returns_empty():
    transport = _routed(
        {"esearch.fcgi": httpx.Response(200, text=_EMPTY_ESEARCH)}
    )
    async with httpx.AsyncClient(transport=transport) as client:
        assert await search_pubmed("nonsense xyz", http_client=client) == []


@pytest.mark.asyncio
async def test_search_pubmed_includes_api_key_when_provided():
    captured: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(str(request.url))
        if _is_esearch(request):
            return httpx.Response(200, text=_ESEARCH)
        return httpx.Response(200, text=_EFETCH)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        await search_pubmed(
            "hip arthroplasty", api_key="my-secret-key", http_client=client
        )
    # The api_key MUST surface in one of the captured URLs
    assert any("api_key=my-secret-key" in u for u in captured)


@pytest.mark.asyncio
async def test_search_pubmed_appends_email_to_request():
    captured: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(str(request.url))
        if _is_esearch(request):
            return httpx.Response(200, text=_ESEARCH)
        return httpx.Response(200, text=_EFETCH)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        await search_pubmed("x", email="research@example.org", http_client=client)
    assert any("email=research%40example.org" in u for u in captured)


@pytest.mark.asyncio
async def test_search_pubmed_handles_5xx_returns_empty():
    transport = _routed({"esearch.fcgi": httpx.Response(503, text="boom")})
    async with httpx.AsyncClient(transport=transport) as client:
        assert await search_pubmed("x", http_client=client) == []


@pytest.mark.asyncio
async def test_search_pubmed_handles_429_with_one_retry():
    calls = {"esearch": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if _is_esearch(request):
            calls["esearch"] += 1
            if calls["esearch"] == 1:
                return httpx.Response(429, text="rate limited")
            return httpx.Response(200, text=_ESEARCH)
        return httpx.Response(200, text=_EFETCH)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        results = await search_pubmed("x", http_client=client, retry_sleep=0.0)

    assert calls["esearch"] == 2  # one retry happened
    assert len(results) >= 1


@pytest.mark.asyncio
async def test_search_pubmed_strips_multi_segment_abstract():
    transport = _routed(
        {
            "esearch.fcgi": httpx.Response(200, text=_ESEARCH),
            "efetch.fcgi": httpx.Response(200, text=_EFETCH),
        }
    )
    async with httpx.AsyncClient(transport=transport) as client:
        results = await search_pubmed("x", http_client=client)
    target = next(r for r in results if r.pmid == "37251234")
    abstract = target.abstract or ""
    # Three labelled segments joined with space
    assert "Surgical approach impacts" in abstract
    assert "We randomised 600 patients" in abstract
    assert "Anterior approach reduced" in abstract


@pytest.mark.asyncio
async def test_fetch_pmid_metadata_batches_ids_into_one_efetch():
    calls = {"efetch": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if _is_efetch(request):
            calls["efetch"] += 1
            return httpx.Response(200, text=_EFETCH)
        raise AssertionError(f"unexpected: {request.url}")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        await fetch_pmid_metadata(["37251234", "36789012"], http_client=client)

    assert calls["efetch"] == 1


@pytest.mark.asyncio
async def test_fetch_pmid_metadata_skips_collective_only_authors():
    transport = _routed({"efetch.fcgi": httpx.Response(200, text=_EFETCH)})
    async with httpx.AsyncClient(transport=transport) as client:
        results = await fetch_pmid_metadata(["37251234"], http_client=client)
    target = next(r for r in results if r.pmid == "37251234")
    # Collective name "THA Investigators Group" must not appear
    assert all("Investigators" not in name for name in target.authors)


@pytest.mark.asyncio
async def test_fetch_pmid_metadata_extracts_doi_from_article_id_list():
    transport = _routed({"efetch.fcgi": httpx.Response(200, text=_EFETCH)})
    async with httpx.AsyncClient(transport=transport) as client:
        results = await fetch_pmid_metadata(["37251234"], http_client=client)
    target = next(r for r in results if r.pmid == "37251234")
    assert target.doi == "10.1001/jama.2023.7770"


@pytest.mark.asyncio
async def test_fetch_pmid_metadata_falls_back_to_medline_date():
    transport = _routed({"efetch.fcgi": httpx.Response(200, text=_EFETCH)})
    async with httpx.AsyncClient(transport=transport) as client:
        results = await fetch_pmid_metadata(["36789012"], http_client=client)
    target = next(r for r in results if r.pmid == "36789012")
    # MedlineDate "2023 Spring" → year 2023
    assert target.year == 2023


def test_constants_point_at_ncbi():
    assert ESEARCH_URL.startswith("https://eutils.ncbi.nlm.nih.gov")
    assert EFETCH_URL.startswith("https://eutils.ncbi.nlm.nih.gov")


# ─── MP12.6 — v2 enrichment + filters ───────────────────────────────────────


@pytest.mark.asyncio
async def test_search_pubmed_sends_sort_relevance_by_default():
    captured: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if _is_esearch(request):
            captured.append(str(request.url))
            return httpx.Response(200, text=_ESEARCH)
        return httpx.Response(200, text=_EFETCH)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        await search_pubmed("hip arthroplasty", http_client=client)

    assert captured, "esearch was not called"
    assert "sort=relevance" in captured[0]


@pytest.mark.asyncio
async def test_search_pubmed_default_retmax_is_50():
    captured: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if _is_esearch(request):
            captured.append(str(request.url))
            return httpx.Response(200, text=_ESEARCH)
        return httpx.Response(200, text=_EFETCH)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        await search_pubmed("x", http_client=client)

    assert "retmax=50" in captured[0]


@pytest.mark.asyncio
async def test_fetch_pmid_metadata_parses_mesh_terms():
    transport = _routed({"efetch.fcgi": httpx.Response(200, text=_EFETCH)})
    async with httpx.AsyncClient(transport=transport) as client:
        results = await fetch_pmid_metadata(["37251234"], http_client=client)
    target = next(r for r in results if r.pmid == "37251234")
    assert "Arthroplasty, Replacement, Hip" in target.mesh_terms
    assert "Humans" in target.mesh_terms
    assert len(target.mesh_terms) >= 3


@pytest.mark.asyncio
async def test_fetch_pmid_metadata_parses_affiliations():
    transport = _routed({"efetch.fcgi": httpx.Response(200, text=_EFETCH)})
    async with httpx.AsyncClient(transport=transport) as client:
        results = await fetch_pmid_metadata(["37251234"], http_client=client)
    target = next(r for r in results if r.pmid == "37251234")
    assert any("Stanford" in a for a in target.affiliations)
    assert any("Harvard" in a for a in target.affiliations)


@pytest.mark.asyncio
async def test_fetch_pmid_metadata_parses_article_types():
    transport = _routed({"efetch.fcgi": httpx.Response(200, text=_EFETCH)})
    async with httpx.AsyncClient(transport=transport) as client:
        results = await fetch_pmid_metadata(["37251234"], http_client=client)
    target = next(r for r in results if r.pmid == "37251234")
    assert "Randomized Controlled Trial" in target.article_types
    assert "Journal Article" in target.article_types


def test_build_esearch_term_no_filters_returns_query_unchanged():
    from research_api.services.ingest.pubmed import build_esearch_term

    assert build_esearch_term("hip arthroplasty", None) == "hip arthroplasty"


def test_build_esearch_term_appends_date_range():
    from research_api.services.ingest.pubmed import (
        PubMedFilters,
        build_esearch_term,
    )

    out = build_esearch_term(
        "hip arthroplasty",
        PubMedFilters(date_from="2020", date_to="2024"),
    )
    assert "hip arthroplasty" in out
    assert "2020[dp]" in out and "2024[dp]" in out
    assert " AND " in out


def test_build_esearch_term_appends_article_types_with_or():
    from research_api.services.ingest.pubmed import (
        PubMedFilters,
        build_esearch_term,
    )

    out = build_esearch_term(
        "anterior approach",
        PubMedFilters(
            article_types=["Randomized Controlled Trial", "Meta-Analysis"]
        ),
    )
    assert '"Randomized Controlled Trial"[pt]' in out
    assert '"Meta-Analysis"[pt]' in out
    assert " OR " in out


def test_build_esearch_term_appends_english_lang():
    from research_api.services.ingest.pubmed import (
        PubMedFilters,
        build_esearch_term,
    )

    out = build_esearch_term("query", PubMedFilters(english_only=True))
    assert "english[lang]" in out


@pytest.mark.asyncio
async def test_search_pubmed_route_passes_filters_to_term():
    """Filters from a request flow through to the esearch term."""
    captured: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if _is_esearch(request):
            captured.append(str(request.url))
            return httpx.Response(200, text=_ESEARCH)
        return httpx.Response(200, text=_EFETCH)

    from research_api.services.ingest.pubmed import PubMedFilters

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        await search_pubmed(
            "approach",
            filters=PubMedFilters(
                date_from="2020",
                date_to="2024",
                article_types=["Review"],
                english_only=True,
            ),
            http_client=client,
        )
    # esearch URL is percent-encoded — the bracket qualifiers survive in the
    # querystring even when encoded as %5B/%5D.
    captured_url = captured[0]
    assert "2020" in captured_url and "2024" in captured_url
    # The encoded form of '"Review"[pt]' contains 'Review' and 'pt'
    assert "Review" in captured_url and "pt" in captured_url
    assert "english" in captured_url
