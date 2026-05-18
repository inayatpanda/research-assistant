"""Phase 8.6 — services/ingest/bibtex.py: BibTeX parser via bibtexparser v1."""
from __future__ import annotations

import logging
from pathlib import Path

from research_api.services.ingest.bibtex import parse_bibtex

_FIXTURES = Path(__file__).parent / "fixtures"


def _zotero() -> str:
    return (_FIXTURES / "bibtex_zotero_sample.bib").read_text(encoding="utf-8")


def _mendeley() -> str:
    return (_FIXTURES / "bibtex_mendeley_sample.bib").read_text(encoding="utf-8")


def _gscholar() -> str:
    return (_FIXTURES / "bibtex_googlescholar_sample.bib").read_text(encoding="utf-8")


def test_parse_bibtex_zotero_round_trip():
    records = parse_bibtex(_zotero())
    assert len(records) == 2
    r0 = records[0]
    assert r0.title.startswith("Anterior versus Posterior")
    assert r0.authors == ["Sarah J. Patel", "Marco Ricci", "Lena Andersson"]
    assert r0.journal == "The New England Journal of Medicine"
    assert r0.year == 2023
    assert r0.volume == "389"
    assert r0.issue == "2"
    # `--` canonicalised to single `-`
    assert r0.pages == "123-134"
    assert r0.doi == "10.1056/NEJMoa2110345"
    assert r0.abstract is not None
    assert r0.source == "bibtex"


def test_parse_bibtex_mendeley_round_trip():
    records = parse_bibtex(_mendeley())
    # @inproceedings is skipped — only the @article survives
    assert len(records) == 1
    r = records[0]
    assert r.authors == ["Wei Chen", "Linh Nguyen"]
    assert r.journal == "JAMA"
    # Brace-armoured title: outer braces stripped
    assert r.title.startswith("Anterior versus posterior")
    assert "{" not in r.title and "}" not in r.title


def test_parse_bibtex_googlescholar_round_trip():
    records = parse_bibtex(_gscholar())
    assert len(records) == 2

    r0 = records[0]
    assert "Robotic-assisted total hip" in r0.title
    assert r0.authors == ["Min Liu", "Hyun Park", "Diego Garcia"]
    assert r0.year == 2024
    assert r0.doi == "10.1016/j.arth.2024.01.005"

    r1 = records[1]
    # Nested braces: outer brace stripping plus inner brace handling
    assert "Total Hip Arthroplasty" in r1.title
    # Author with brace-armoured surname
    assert "O'Neill" in r1.authors[1]


def test_parse_bibtex_strips_brace_armor_on_titles():
    text = (
        "@article{x, "
        "title={Total Hip {Arthroplasty}}, "
        "author={Smith, Jane}, "
        "year={2023}}\n"
    )
    [r] = parse_bibtex(text)
    assert "{" not in r.title
    assert "}" not in r.title


def test_parse_bibtex_handles_multiple_authors_split_on_and():
    text = (
        "@article{x, "
        "title={t}, "
        "author={Smith, Jane and Doe, John and Park, Hyun}, "
        "year={2023}}\n"
    )
    [r] = parse_bibtex(text)
    assert r.authors == ["Jane Smith", "John Doe", "Hyun Park"]


def test_parse_bibtex_skips_non_article_entries():
    text = (
        "@book{b1, title={A book}, author={X}, year={2020}}\n"
        "@article{a1, title={An article}, author={Y}, year={2021}}\n"
    )
    rs = parse_bibtex(text)
    assert len(rs) == 1
    assert rs[0].title == "An article"


def test_parse_bibtex_handles_inproceedings_entry_silently_skipped():
    text = (
        "@inproceedings{ip1, title={Proc}, author={A}, year={2020}}\n"
    )
    assert parse_bibtex(text) == []


def test_parse_bibtex_corrupted_input_returns_empty_list_logs_warning(caplog):
    with caplog.at_level(logging.WARNING):
        rs = parse_bibtex("this is not @bibtex at all { broken")
    assert rs == []


def test_parse_bibtex_source_is_bibtex_on_every_record():
    rs = parse_bibtex(_zotero())
    assert all(r.source == "bibtex" for r in rs)


def test_parse_bibtex_journaltitle_field_supported():
    text = (
        "@article{x, title={t}, author={Smith, Jane}, "
        "journaltitle={Journal Title}, year={2023}}\n"
    )
    [r] = parse_bibtex(text)
    assert r.journal == "Journal Title"


def test_parse_bibtex_issue_field_supported():
    text = (
        "@article{x, title={t}, author={Smith, Jane}, "
        "journal={J}, issue={5}, year={2023}}\n"
    )
    [r] = parse_bibtex(text)
    assert r.issue == "5"


def test_parse_bibtex_empty_input_returns_empty():
    assert parse_bibtex("") == []
    assert parse_bibtex("    \n   \n") == []
