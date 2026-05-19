"""Phase 19 (MP19) — MeSH NCBI E-utilities wrapper + XML parser."""
from __future__ import annotations

import pytest
import respx
from httpx import Response

from research_api.services.ingest.mesh import (
    ESEARCH_URL,
    EFETCH_URL,
    fetch_mesh,
    parse_mesh_xml,
    search_mesh,
)


_SAMPLE_MESH_XML = """<?xml version="1.0"?>
<DescriptorRecordSet>
  <DescriptorRecord>
    <DescriptorUI>D013313</DescriptorUI>
    <DescriptorName>
      <String>Hip Replacement, Total</String>
    </DescriptorName>
    <ConceptList>
      <Concept>
        <ScopeNote>Total replacement of the hip joint.</ScopeNote>
      </Concept>
    </ConceptList>
    <TreeNumberList>
      <TreeNumber>E04.555.395</TreeNumber>
      <TreeNumber>E04.580.395</TreeNumber>
    </TreeNumberList>
    <ConceptList>
      <Concept>
        <TermList>
          <Term>
            <String>Total Hip Replacement</String>
          </Term>
          <Term>
            <String>THR</String>
          </Term>
        </TermList>
      </Concept>
    </ConceptList>
  </DescriptorRecord>
  <DescriptorRecord>
    <DescriptorUI>D000855</DescriptorUI>
    <DescriptorName>
      <String>Anesthesia, Spinal</String>
    </DescriptorName>
    <TreeNumberList>
      <TreeNumber>E03.155.086</TreeNumber>
    </TreeNumberList>
  </DescriptorRecord>
</DescriptorRecordSet>
"""

_SAMPLE_ESEARCH_XML = """<?xml version="1.0"?>
<eSearchResult>
  <Count>2</Count>
  <IdList>
    <Id>68013313</Id>
    <Id>68000855</Id>
  </IdList>
</eSearchResult>
"""


def test_parse_mesh_xml_extracts_descriptors():
    descs = parse_mesh_xml(_SAMPLE_MESH_XML)
    assert len(descs) == 2
    first = descs[0]
    assert first.descriptor_ui == "D013313"
    assert first.descriptor_name == "Hip Replacement, Total"
    assert "Total replacement" in (first.scope_note or "")
    assert "E04.555.395" in first.tree_numbers
    assert "E04.580.395" in first.tree_numbers
    assert "Total Hip Replacement" in first.entry_terms
    assert "THR" in first.entry_terms

    second = descs[1]
    assert second.descriptor_ui == "D000855"
    assert second.descriptor_name == "Anesthesia, Spinal"
    assert second.scope_note is None
    assert second.entry_terms == []


def test_parse_mesh_xml_returns_empty_on_unknown_shape():
    descs = parse_mesh_xml("<root><other/></root>")
    assert descs == []


@pytest.mark.asyncio
@respx.mock
async def test_search_mesh_chains_esearch_then_efetch():
    respx.get(ESEARCH_URL).respond(text=_SAMPLE_ESEARCH_XML, status_code=200)
    respx.get(EFETCH_URL).respond(text=_SAMPLE_MESH_XML, status_code=200)

    descs = await search_mesh("total hip arthroplasty")
    assert len(descs) == 2
    assert descs[0].descriptor_ui == "D013313"


@pytest.mark.asyncio
@respx.mock
async def test_search_mesh_empty_query_returns_empty():
    descs = await search_mesh("   ")
    assert descs == []


@pytest.mark.asyncio
@respx.mock
async def test_search_mesh_handles_429_retry_then_success():
    respx.get(ESEARCH_URL).mock(
        side_effect=[Response(429), Response(200, text=_SAMPLE_ESEARCH_XML)]
    )
    respx.get(EFETCH_URL).respond(text=_SAMPLE_MESH_XML, status_code=200)
    descs = await search_mesh("hip", retry_sleep=0)
    assert len(descs) == 2


@pytest.mark.asyncio
@respx.mock
async def test_search_mesh_network_error_returns_empty():
    import httpx

    respx.get(ESEARCH_URL).mock(side_effect=httpx.TimeoutException("boom"))
    descs = await search_mesh("hip", retry_sleep=0)
    assert descs == []


@pytest.mark.asyncio
@respx.mock
async def test_fetch_mesh_empty_list_short_circuits():
    descs = await fetch_mesh([])
    assert descs == []


@pytest.mark.asyncio
@respx.mock
async def test_search_mesh_500_response_returns_empty():
    respx.get(ESEARCH_URL).respond(status_code=500)
    descs = await search_mesh("anything", retry_sleep=0)
    assert descs == []
