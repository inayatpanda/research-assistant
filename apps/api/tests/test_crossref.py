import httpx
import pytest

from research_api.services.crossref import lookup_doi, normalise_doi


_SAMPLE_RESPONSE = {
    "message": {
        "DOI": "10.1234/jor.2024.0001",
        "title": ["Anterior approach in total hip arthroplasty"],
        "author": [
            {"given": "John", "family": "Doe"},
            {"given": "Jane", "family": "Smith"},
        ],
        "container-title": ["J Orthopaedic Research"],
        "issued": {"date-parts": [[2024, 5, 1]]},
        "volume": "42",
        "issue": "3",
        "page": "100-110",
    }
}


def _mock_transport(handler):
    return httpx.MockTransport(handler)


def test_normalise_doi_strips_prefixes():
    assert normalise_doi("https://doi.org/10.1234/abc") == "10.1234/abc"
    assert normalise_doi("doi:10.1234/abc") == "10.1234/abc"
    assert normalise_doi("DOI:10.1234/abc") == "10.1234/abc"
    assert normalise_doi("10.1234/abc") == "10.1234/abc"


def test_normalise_doi_rejects_malformed():
    assert normalise_doi("not-a-doi") is None
    assert normalise_doi("10/abc") is None  # too few digits
    assert normalise_doi("") is None
    assert normalise_doi(None) is None  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_lookup_doi_happy_path():
    def handler(request):
        return httpx.Response(200, json=_SAMPLE_RESPONSE)

    async with httpx.AsyncClient(transport=_mock_transport(handler)) as client:
        meta = await lookup_doi("10.1234/jor.2024.0001", http_client=client)
    assert meta is not None
    assert meta.title.startswith("Anterior approach")
    assert meta.authors == ["John Doe", "Jane Smith"]
    assert meta.journal == "J Orthopaedic Research"
    assert meta.year == 2024
    assert meta.volume == "42"
    assert meta.issue == "3"
    assert meta.pages == "100-110"
    assert meta.doi == "10.1234/jor.2024.0001"
    assert meta.confidence == 1.0


@pytest.mark.asyncio
async def test_lookup_doi_404_returns_none():
    def handler(request):
        return httpx.Response(404, json={})

    async with httpx.AsyncClient(transport=_mock_transport(handler)) as client:
        assert await lookup_doi("10.1234/missing", http_client=client) is None


@pytest.mark.asyncio
async def test_lookup_doi_5xx_returns_none():
    def handler(request):
        return httpx.Response(503, json={})

    async with httpx.AsyncClient(transport=_mock_transport(handler)) as client:
        assert await lookup_doi("10.1234/oops", http_client=client) is None


@pytest.mark.asyncio
async def test_lookup_doi_malformed_skips_http():
    called = False

    def handler(request):
        nonlocal called
        called = True
        return httpx.Response(200, json=_SAMPLE_RESPONSE)

    async with httpx.AsyncClient(transport=_mock_transport(handler)) as client:
        assert await lookup_doi("not-a-doi", http_client=client) is None
    assert called is False
