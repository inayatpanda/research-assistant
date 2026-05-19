"""Phase 19 (MP19) — PICO-driven MeSH suggester."""
from __future__ import annotations

import pytest
import respx

from research_api.services.ingest.mesh import ESEARCH_URL, EFETCH_URL
from research_api.services.ingest.mesh_suggester import (
    compose_pico_term,
    suggest_mesh_from_pico,
)


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
  </DescriptorRecord>
</DescriptorRecordSet>
"""


def test_compose_pico_term_single_field():
    term = compose_pico_term({
        "population": "hip arthroplasty",
        "intervention": None,
        "comparator": None,
        "outcome": None,
    })
    assert term == '"hip arthroplasty"'


def test_compose_pico_term_multiple_fields_or_joined():
    term = compose_pico_term({
        "population": "hip arthroplasty",
        "intervention": "spinal anesthesia",
        "comparator": "general anesthesia",
        "outcome": "mortality",
    })
    assert " OR " in term
    assert '"hip arthroplasty"' in term
    assert '"spinal anesthesia"' in term
    assert '"general anesthesia"' in term
    assert "mortality" in term


def test_compose_pico_term_strips_empty():
    term = compose_pico_term({
        "population": "",
        "intervention": "   ",
        "comparator": None,
        "outcome": "pain",
    })
    assert term == "pain"


def test_compose_pico_term_all_empty_returns_empty():
    assert compose_pico_term({
        "population": None, "intervention": "", "comparator": "  ", "outcome": None,
    }) == ""


@pytest.mark.asyncio
@respx.mock
async def test_suggest_mesh_from_pico_returns_descriptors():
    respx.get(ESEARCH_URL).respond(text=_SAMPLE_ESEARCH, status_code=200)
    respx.get(EFETCH_URL).respond(text=_SAMPLE_FETCH, status_code=200)

    descs = await suggest_mesh_from_pico({
        "population": "hip arthroplasty",
        "intervention": "spinal anesthesia",
        "comparator": None,
        "outcome": None,
    })
    assert len(descs) == 1
    assert descs[0].descriptor_ui == "D013313"


@pytest.mark.asyncio
@respx.mock
async def test_suggest_mesh_from_pico_empty_pico_returns_empty():
    descs = await suggest_mesh_from_pico({
        "population": None, "intervention": None, "comparator": None, "outcome": None,
    })
    assert descs == []
