"""F1 — DOI regex + heuristic title/authors/year extraction.

Pure-function tests, no HTTP, no DB. Verifies the algorithm against six
hand-curated DOI shapes plus a couple of heuristic fixtures.
"""
from __future__ import annotations

from research_api.services.ingest.pdf_metadata import (
    extract_doi_from_text,
    extract_heuristic_metadata,
)


# -----------------------------------------------------------------------------
# DOI extraction
# -----------------------------------------------------------------------------


def test_extracts_clean_doi():
    assert (
        extract_doi_from_text("doi: 10.1234/foo.bar")
        == "10.1234/foo.bar"
    )


def test_strips_trailing_period():
    # Sentence-final periods are common in JATS bibliographies and abstracts.
    assert (
        extract_doi_from_text("See 10.1016/j.jclinepi.2019.07.005.")
        == "10.1016/j.jclinepi.2019.07.005"
    )


def test_strips_trailing_paren():
    # CrossRef sometimes wraps the DOI in parentheses inline.
    assert (
        extract_doi_from_text("(10.1234/abc.def)")
        == "10.1234/abc.def"
    )


def test_finds_doi_mid_text():
    text = "Lorem ipsum dolor sit amet 10.5555/x.y.z, consectetur adipiscing."
    assert extract_doi_from_text(text) == "10.5555/x.y.z"


def test_returns_none_when_no_doi():
    assert extract_doi_from_text("No DOI in this string") is None
    assert extract_doi_from_text("") is None


def test_picks_first_of_two_dois():
    text = "Cite both: 10.1111/aaaa and also 10.2222/bbbb later."
    assert extract_doi_from_text(text) == "10.1111/aaaa"


# -----------------------------------------------------------------------------
# Heuristic extraction
# -----------------------------------------------------------------------------


def test_heuristic_picks_title_and_authors_and_year():
    text = "\n".join(
        [
            "Journal of Fictitious Studies",  # 4 words — too short for title
            "A Randomised Controlled Trial of Foo in Bar Patients",  # 10 words → title
            "Alice Author, Bob Bear, Carol Cole",  # authors
            "Published 2024.",
        ]
    )
    out = extract_heuristic_metadata(text)
    assert out["title"] == "A Randomised Controlled Trial of Foo in Bar Patients"
    assert out["authors"] == ["Alice Author", "Bob Bear", "Carol Cole"]
    assert out["year"] == 2024


def test_heuristic_empty_text_returns_empty_dict():
    assert extract_heuristic_metadata("") == {}


def test_heuristic_ignores_affiliation_lines_for_authors():
    # The author line is suspiciously long → we skip writing the authors key.
    text = "\n".join(
        [
            "Trial of Foo for Bar in Adults With Clinical Disease",
            "Department of Made Up Things, University of Nowhere, 1234 Imaginary Street",
            "Year 2021.",
        ]
    )
    out = extract_heuristic_metadata(text)
    assert "title" in out
    assert "authors" not in out
    assert out["year"] == 2021
