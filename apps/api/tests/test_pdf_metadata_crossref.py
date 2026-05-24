"""F1 — Crossref enrichment leg of ``extract_metadata_for_pdf``.

Mocks the Crossref endpoint with respx so we exercise the network leg
without hitting the live API. Three cases: success, 404, network down.
"""
from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx
from httpx import Response

from research_api.services.ingest.pdf_metadata import (
    enrich_via_crossref,
    extract_metadata_for_pdf,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _crossref_sample() -> dict:
    return json.loads((FIXTURES / "crossref_sample.json").read_text())


@pytest.mark.asyncio
async def test_enrich_via_crossref_returns_dict_on_hit():
    with respx.mock(base_url="https://api.crossref.org") as mock:
        mock.get("/works/10.1056/NEJMoa2110345").mock(
            return_value=Response(200, json=_crossref_sample())
        )
        out = await enrich_via_crossref("10.1056/NEJMoa2110345")
    assert out is not None
    assert out["title"].startswith("Anterior versus Posterior")
    assert out["journal"] == "The New England Journal of Medicine"
    assert out["year"] == 2023
    assert out["volume"] == "389"
    assert out["doi"] == "10.1056/NEJMoa2110345"
    assert isinstance(out["authors"], list) and len(out["authors"]) == 3


@pytest.mark.asyncio
async def test_enrich_via_crossref_returns_none_on_404():
    with respx.mock(base_url="https://api.crossref.org") as mock:
        mock.get("/works/10.9999/missing").mock(return_value=Response(404))
        out = await enrich_via_crossref("10.9999/missing")
    assert out is None


@pytest.mark.asyncio
async def test_enrich_via_crossref_returns_none_on_network_error():
    with respx.mock(base_url="https://api.crossref.org") as mock:
        mock.get("/works/10.1234/x.y").mock(
            side_effect=httpx.ConnectError("boom")
        )
        out = await enrich_via_crossref("10.1234/x.y")
    assert out is None


# -- extract_metadata_for_pdf orchestrator -----------------------------------


def _pdf_with_text(text: str) -> bytes:
    """Build a tiny in-memory PDF containing ``text``."""
    try:
        from pypdf import PdfWriter
    except Exception:  # pragma: no cover
        pytest.skip("pypdf unavailable")

    # The route's text extractor only really needs *some* text; the simplest
    # cross-version approach is to use the reportlab-free pypdf trick of
    # writing a page with an annotation. But reportlab is not in deps, so
    # we instead lean on the existing fixtures sample.pdf and append the
    # text via a stamp. Easiest path: just return our static fixture and
    # rely on the test that uses this to monkeypatch the extractor.
    raise NotImplementedError


@pytest.mark.asyncio
async def test_extract_metadata_for_pdf_uses_crossref_when_doi_found(monkeypatch):
    # Stub the text extractor so we don't have to render a PDF on the fly.
    import research_api.services.ingest.pdf_metadata as mod

    monkeypatch.setattr(
        mod,
        "extract_first_pages_text",
        lambda data, n=5: "Some intro text. doi: 10.1056/NEJMoa2110345 More.",
    )
    with respx.mock(base_url="https://api.crossref.org") as mock:
        mock.get("/works/10.1056/NEJMoa2110345").mock(
            return_value=Response(200, json=_crossref_sample())
        )
        out = await extract_metadata_for_pdf(b"%PDF-1.4 fake bytes")
    assert out["autofill_status"] == "doi_match"
    assert out["fields"]["title"].startswith("Anterior versus Posterior")
    assert all(prov == "doi" for prov in out["provenance"].values())


@pytest.mark.asyncio
async def test_extract_metadata_for_pdf_falls_back_to_heuristics(monkeypatch):
    import research_api.services.ingest.pdf_metadata as mod

    text = "\n".join(
        [
            "Short Header",
            "A Heuristic Title That Spans Roughly Ten Words For Demo Purposes",
            "Jane Doe, John Smith",
            "Published 2022.",
        ]
    )
    monkeypatch.setattr(mod, "extract_first_pages_text", lambda data, n=5: text)
    # No DOI in text — Crossref should never be called.
    out = await extract_metadata_for_pdf(b"%PDF-1.4 fake bytes")
    assert out["autofill_status"] == "heuristic_only"
    assert "title" in out["fields"]
    assert out["fields"]["year"] == 2022
    assert all(prov == "heuristic" for prov in out["provenance"].values())


@pytest.mark.asyncio
async def test_extract_metadata_for_pdf_failed_when_no_text(monkeypatch):
    import research_api.services.ingest.pdf_metadata as mod

    monkeypatch.setattr(mod, "extract_first_pages_text", lambda data, n=5: "")
    out = await extract_metadata_for_pdf(b"%PDF-1.4 ")
    assert out["autofill_status"] == "failed"
    assert out["fields"] == {}
    assert out["provenance"] == {}
