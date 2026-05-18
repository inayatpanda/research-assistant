"""Phase 8.6 — services/ingest/ris.py: RIS parser."""
from __future__ import annotations

from pathlib import Path

from research_api.services.ingest.ris import parse_ris

_FIXTURES = Path(__file__).parent / "fixtures"


def _zotero() -> str:
    return (_FIXTURES / "ris_zotero_sample.ris").read_text(encoding="utf-8")


def _pubmed_export() -> str:
    return (_FIXTURES / "ris_pubmed_export_sample.ris").read_text(encoding="utf-8")


def test_parse_ris_zotero_export_round_trip():
    records = parse_ris(_zotero())
    assert len(records) == 3

    r0 = records[0]
    assert r0.title.startswith("Anterior approach")
    assert r0.authors == ["Sarah J. Patel", "Marco Ricci", "Lena Andersson"]
    assert r0.journal == "The New England Journal of Medicine"
    assert r0.year == 2023
    assert r0.volume == "389"
    assert r0.issue == "2"
    assert r0.pages == "123-134"
    assert r0.doi == "10.1056/NEJMoa2110345"
    assert r0.abstract and "second AB line" in r0.abstract
    assert r0.source == "ris"

    r1 = records[1]
    assert r1.title == "Posterior approach long-term outcomes"
    assert r1.year == 2022  # Y1 fallback

    r2 = records[2]
    # A1 tag + T2 tag exercise the alternate journal/author paths
    assert r2.journal == "JAMA"
    assert r2.authors == ["Wei Chen", "Linh Nguyen"]


def test_parse_ris_pubmed_export_round_trip():
    records = parse_ris(_pubmed_export())
    assert len(records) == 2
    r = records[0]
    assert r.title.startswith("Direct anterior")
    # N2 → abstract (pubmed-style)
    assert r.abstract and "Methods line" in r.abstract
    # JT → journal preferred over TA (TA is iso abbreviation)
    assert r.journal == "The Journal of Bone and Joint Surgery"
    # Pages without separate EP — SP carries the whole range
    assert r.pages == "333-340"


def test_parse_ris_normalises_author_last_first_to_first_last():
    text = "TY  - JOUR\nTI  - x\nAU  - Smith, Jane Q.\nER  -\n"
    [r] = parse_ris(text)
    assert r.authors == ["Jane Q. Smith"]


def test_parse_ris_keeps_already_first_last_authors_unchanged():
    text = "TY  - JOUR\nTI  - x\nAU  - Jane Smith\nER  -\n"
    [r] = parse_ris(text)
    assert r.authors == ["Jane Smith"]


def test_parse_ris_concatenates_multi_line_abstract():
    text = "TY  - JOUR\nTI  - X\nAB  - one\nAB  - two\nAB  - three\nER  -\n"
    [r] = parse_ris(text)
    assert r.abstract == "one two three"


def test_parse_ris_handles_missing_pages_gracefully():
    text = "TY  - JOUR\nTI  - x\nVL  - 12\nER  -\n"
    [r] = parse_ris(text)
    assert r.pages is None
    assert r.volume == "12"


def test_parse_ris_drops_record_without_title():
    text = "TY  - JOUR\nAU  - x\nER  -\n"
    assert parse_ris(text) == []


def test_parse_ris_handles_crlf_lf_mixed_newlines():
    text = "TY  - JOUR\r\nTI  - x\r\nER  -\r\nTY  - JOUR\nTI  - y\nER  -\n"
    rs = parse_ris(text)
    assert [r.title for r in rs] == ["x", "y"]


def test_parse_ris_empty_input_returns_empty_list():
    assert parse_ris("") == []
    assert parse_ris("   \n   \n") == []


def test_parse_ris_source_is_ris_on_every_record():
    rs = parse_ris(_zotero())
    assert all(r.source == "ris" for r in rs)


def test_parse_ris_year_extracted_from_partial_date():
    text = "TY  - JOUR\nTI  - x\nPY  - 2024-05\nER  -\n"
    [r] = parse_ris(text)
    assert r.year == 2024
