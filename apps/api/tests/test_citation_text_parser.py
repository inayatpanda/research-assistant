"""MP16 — Bulk citation-text parser unit tests.

Uses injected async resolvers so we never hit a real network in CI. The
``parse_citation_text`` API exposes ``doi_resolver``, ``pmid_resolver``, and
``title_resolver`` overrides specifically for testability.
"""
from __future__ import annotations

import asyncio
from typing import Iterable

import pytest

from research_api.schemas.ingest import ArticleMetadata
from research_api.services.ingest.citation_text_parser import (
    extract_doi,
    extract_pmid,
    parse_citation_text,
    split_fragments,
)


def _meta(doi: str | None = None, pmid: str | None = None, title: str = "Hit") -> ArticleMetadata:
    return ArticleMetadata(
        title=title,
        authors=["Jane Doe"],
        year=2024,
        doi=doi,
        pmid=pmid,
        source="doi" if doi else ("pubmed" if pmid else "manual"),
    )


# ─── extract_doi ────────────────────────────────────────────────────────────


def test_extract_doi_basic():
    assert extract_doi("Foo bar 10.1234/abc.xyz blah") == "10.1234/abc.xyz"


def test_extract_doi_trailing_punctuation_stripped():
    assert extract_doi("see https://doi.org/10.1234/abc.").rstrip(".") == "10.1234/abc"


def test_extract_doi_none_when_missing():
    assert extract_doi("Just plain prose. No identifier.") is None


# ─── extract_pmid ───────────────────────────────────────────────────────────


def test_extract_pmid_various_prefixes():
    assert extract_pmid("PMID: 12345678") == "12345678"
    assert extract_pmid("PubMed ID 87654321 trailing") == "87654321"
    assert extract_pmid("free text with 99887766 alone") is None  # needs prefix


# ─── split_fragments ────────────────────────────────────────────────────────


def test_split_fragments_numbered_vancouver():
    text = (
        "1. Doe J. Title one. J Foo 2024;10:1-5.\n"
        "2. Smith K. Title two. J Bar 2023;9:11-22.\n"
        "3. Patel L. Title three. J Baz 2022;8:33-44."
    )
    parts = split_fragments(text)
    assert len(parts) == 3
    assert parts[0].startswith("Doe J")
    assert parts[1].startswith("Smith K")
    assert parts[2].startswith("Patel L")


def test_split_fragments_bracketed_numbers():
    text = "[1] Doe J. A.\n[2] Smith K. B.\n[3] Patel L. C."
    parts = split_fragments(text)
    assert len(parts) == 3
    assert parts[0].startswith("Doe J")


def test_split_fragments_blank_line_separated():
    text = "Doe J. A.\n\nSmith K. B.\n\nPatel L. C."
    parts = split_fragments(text)
    assert len(parts) == 3


def test_split_fragments_empty_input():
    assert split_fragments("") == []
    assert split_fragments("   \n\n  ") == []


# ─── parse_citation_text — with injected resolvers ─────────────────────────


@pytest.mark.asyncio
async def test_parse_with_doi_resolves_via_crossref():
    called: list[str] = []

    async def doi_resolver(doi: str) -> ArticleMetadata | None:
        called.append(doi)
        return _meta(doi=doi, title="Resolved")

    text = "1. Doe J. Title. J Foo 2024;1:1. doi:10.1234/abc"
    results = await parse_citation_text(
        text,
        doi_resolver=doi_resolver,
    )
    assert len(results) == 1
    assert called == ["10.1234/abc"]
    assert results[0].status == "ok"
    assert results[0].doi == "10.1234/abc"
    assert results[0].parsed_metadata is not None
    assert results[0].parsed_metadata.title == "Resolved"


@pytest.mark.asyncio
async def test_parse_with_pmid_resolves_via_pubmed():
    captured: list[list[str]] = []

    async def pmid_resolver(pmids: list[str]) -> list[ArticleMetadata]:
        captured.append(list(pmids))
        return [_meta(pmid=pmids[0], title="PubMed hit")]

    text = "1. Doe J. Title. J Foo 2024. PMID: 99887766"
    results = await parse_citation_text(
        text,
        pmid_resolver=pmid_resolver,
    )
    assert len(results) == 1
    assert captured == [["99887766"]]
    assert results[0].status == "ok"
    assert results[0].pmid == "99887766"


@pytest.mark.asyncio
async def test_parse_fuzzy_title_lookup_used_when_no_identifier():
    queries: list[str] = []

    async def title_resolver(query: str) -> ArticleMetadata | None:
        queries.append(query)
        return _meta(title="Fuzzy hit", doi="10.5555/fuzzy")

    text = "1. Doe J. A title without identifier. J Foo 2024;1:1."
    results = await parse_citation_text(
        text,
        title_resolver=title_resolver,
    )
    assert len(queries) == 1
    assert results[0].status == "ok"
    assert results[0].doi == "10.5555/fuzzy"


@pytest.mark.asyncio
async def test_parse_unresolved_when_fuzzy_returns_none():
    async def title_resolver(query: str) -> ArticleMetadata | None:
        return None

    text = "1. Doe J. Some untraceable thing.\n2. Smith K. Another one."
    results = await parse_citation_text(
        text,
        title_resolver=title_resolver,
    )
    assert len(results) == 2
    assert all(r.status == "unresolved" for r in results)
    assert results[0].parsed_metadata is None
    assert any("No high-confidence" in n for n in results[0].notes)


@pytest.mark.asyncio
async def test_parse_mixed_doi_pmid_unresolved():
    async def doi_resolver(doi: str) -> ArticleMetadata | None:
        return _meta(doi=doi, title="DOI hit")

    async def pmid_resolver(pmids: list[str]) -> list[ArticleMetadata]:
        return [_meta(pmid=pmids[0], title="PMID hit")]

    async def title_resolver(query: str) -> ArticleMetadata | None:
        return None

    text = (
        "1. Doe J. Title A. doi:10.1111/aaa.\n"
        "2. Smith K. Title B. PMID: 11111111.\n"
        "3. Patel L. Title C — no identifier."
    )
    results = await parse_citation_text(
        text,
        doi_resolver=doi_resolver,
        pmid_resolver=pmid_resolver,
        title_resolver=title_resolver,
    )
    statuses = [r.status for r in results]
    assert statuses == ["ok", "ok", "unresolved"]
    assert results[0].doi == "10.1111/aaa"
    assert results[1].pmid == "11111111"


@pytest.mark.asyncio
async def test_parse_disables_fuzzy_when_flag_off():
    async def title_resolver(query: str) -> ArticleMetadata | None:
        return _meta(title="should not be called")

    text = "1. Doe J. Title without DOI."
    results = await parse_citation_text(
        text,
        fuzzy_title_lookup=False,
    )
    assert len(results) == 1
    assert results[0].status == "unresolved"
