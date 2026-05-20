"""Phase 16 (MP16) — Bulk citation-text parser.

Splits a paste of free-form citation text into individual reference
fragments, then attempts to resolve each fragment to authoritative metadata
via the following waterfall:

  1. DOI regex hit → Crossref lookup (``services.ingest.crossref``).
  2. PMID regex hit → PubMed ``fetch_pmid_metadata``.
  3. Neither — fuzzy title search via Crossref's ``?query.title=`` endpoint;
     the top result is accepted only when the relevance score exceeds 80.
  4. None of the above → returned as ``status="unresolved"``.

Pure, deterministic input/output. All HTTP calls go through ``httpx``
clients that the caller can swap for a ``respx``-mocked client in tests —
the ``parse_citation_text`` async function accepts an optional ``http_client``
plus an optional Crossref-search override for unit testing.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Awaitable, Callable
from urllib.parse import quote

import httpx

from ...schemas.ingest import ArticleMetadata
from .crossref import lookup_doi_metadata
from .pubmed import fetch_pmid_metadata

# DOI per https://www.crossref.org/blog/dois-and-matching-regular-expressions/
_DOI_RE = re.compile(
    r"\b(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)", re.IGNORECASE
)
# Strip trailing punctuation that's almost certainly not part of the DOI.
_DOI_TRAILING = re.compile(r"[.,;:)\]]+$")
_PMID_RE = re.compile(r"(?:PMID|PubMed\s*ID|PMCID)\s*[:#]?\s*(\d{4,9})", re.IGNORECASE)

# Splitters:
#   - leading "1. " / "[1] " / "1) " followed by content
#   - or two-or-more newlines
_NUMBERED_PREFIX_RE = re.compile(
    r"(?m)^\s*(?:\[\d+\]|\d+[.)])\s+"
)
_BLANK_LINE_RE = re.compile(r"\n\s*\n+")

CROSSREF_BASE = "https://api.crossref.org/works"


@dataclass
class ParsedReference:
    """Single parsed-and-(maybe)-resolved reference fragment."""

    raw: str
    doi: str | None = None
    pmid: str | None = None
    parsed_metadata: ArticleMetadata | None = None
    status: str = "unresolved"  # "ok" | "unresolved"
    # Reason populated when the parser bailed; surfaced to the UI so the
    # user can decide whether to enter the missing metadata manually.
    notes: list[str] = field(default_factory=list)


# ─── Fragment splitting ─────────────────────────────────────────────────────


def split_fragments(text: str) -> list[str]:
    """Split a free-form citation blob into individual fragments.

    Tries (in order):
      1. Numbered prefixes (``1. ``, ``[1] ``, ``1) ``) — most reliable.
      2. Two-or-more newlines — falls back when the paste is not numbered.
      3. Otherwise returns the whole text as one fragment.

    Output is whitespace-trimmed and empty fragments are dropped.
    """
    if not text or not text.strip():
        return []
    # If the text starts with a numbered prefix, split on numbered prefixes.
    if _NUMBERED_PREFIX_RE.search(text):
        parts = _NUMBERED_PREFIX_RE.split(text)
        # `re.split` keeps the leading piece (before the first match); drop
        # it if empty/whitespace.
        cleaned = [p.strip() for p in parts if p.strip()]
        if cleaned:
            return cleaned
    # Fall back to blank-line splitting.
    by_blank = [p.strip() for p in _BLANK_LINE_RE.split(text) if p.strip()]
    if len(by_blank) >= 2:
        return by_blank
    # Last resort: line-by-line if author-start pattern matches >= 2 lines.
    line_split = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if len(line_split) >= 2 and all(
        re.match(r"^[A-Z][a-z]+", ln) for ln in line_split[:2]
    ):
        return line_split
    return [text.strip()]


def extract_doi(fragment: str) -> str | None:
    """Pull the first DOI-looking token out of a citation fragment."""
    m = _DOI_RE.search(fragment)
    if not m:
        return None
    doi = _DOI_TRAILING.sub("", m.group(1))
    return doi if doi else None


def extract_pmid(fragment: str) -> str | None:
    """Pull a ``PMID: 12345678``-style identifier out of a fragment."""
    m = _PMID_RE.search(fragment)
    return m.group(1) if m else None


# ─── Crossref fuzzy title search ────────────────────────────────────────────


async def crossref_search_by_title(
    query: str,
    *,
    http_client: httpx.AsyncClient | None = None,
    timeout: float = 10.0,
    email: str = "noreply@research-assistant.local",
    score_threshold: float = 80.0,
) -> ArticleMetadata | None:
    """Fuzzy-search Crossref by bibliographic / title query.

    Returns the top result if its Crossref relevance score exceeds
    ``score_threshold`` (defaults to 80 — Crossref scores are non-normalised,
    so 80+ is empirically the "high confidence" threshold).
    """
    if not query.strip():
        return None
    own = http_client is None
    client = http_client or httpx.AsyncClient(timeout=timeout)
    try:
        params = {
            "query.bibliographic": query,
            "rows": "3",
        }
        r = await client.get(
            CROSSREF_BASE,
            params=params,
            headers={
                "User-Agent": (
                    f"ResearchManuscriptAssistant/0.0.1 (mailto:{email})"
                ),
            },
        )
        if r.status_code != 200:
            return None
        message = (r.json() or {}).get("message", {})
        items = message.get("items") or []
        if not items:
            return None
        top = items[0]
        score = float(top.get("score") or 0.0)
        if score < score_threshold:
            return None
        return _crossref_item_to_metadata(top)
    except (httpx.HTTPError, ValueError, KeyError):
        return None
    finally:
        if own:
            await client.aclose()


def _crossref_item_to_metadata(msg: dict) -> ArticleMetadata:
    """Convert a Crossref ``works`` item to ``ArticleMetadata``.

    Mirrors ``services.ingest.crossref._to_metadata`` but the search-result
    shape is slightly different (no top-level wrapper), so we keep this
    locally rather than importing the private function.
    """
    title_list = msg.get("title") or []
    title = title_list[0] if title_list else "Untitled"
    authors = [
        f"{a.get('given', '').strip()} {a.get('family', '').strip()}".strip()
        for a in (msg.get("author") or [])
        if a.get("given") or a.get("family")
    ]
    journal_list = msg.get("container-title") or []
    journal = journal_list[0] if journal_list else None
    year = None
    issued = msg.get("issued", {}).get("date-parts") or msg.get(
        "published-print", {}
    ).get("date-parts")
    if issued and issued[0]:
        try:
            year = int(issued[0][0])
        except (TypeError, ValueError):
            year = None
    doi = msg.get("DOI")
    return ArticleMetadata(
        title=title,
        authors=authors,
        journal=journal,
        year=year,
        volume=msg.get("volume"),
        issue=msg.get("issue"),
        pages=msg.get("page"),
        doi=doi,
        pmid=None,
        abstract=None,
        source="doi" if doi else "manual",
    )


# ─── Public API ─────────────────────────────────────────────────────────────


# Async resolver signatures the caller may inject in tests.
DoiResolver = Callable[[str], Awaitable[ArticleMetadata | None]]
PmidResolver = Callable[[list[str]], Awaitable[list[ArticleMetadata]]]
TitleResolver = Callable[[str], Awaitable[ArticleMetadata | None]]


async def parse_citation_text(
    text: str,
    *,
    http_client: httpx.AsyncClient | None = None,
    doi_resolver: DoiResolver | None = None,
    pmid_resolver: PmidResolver | None = None,
    title_resolver: TitleResolver | None = None,
    fuzzy_title_lookup: bool = True,
    email: str = "noreply@research-assistant.local",
    api_key: str | None = None,
) -> list[ParsedReference]:
    """Parse + resolve a pasted block of citation text.

    Returns one ``ParsedReference`` per detected fragment, in input order.
    """
    fragments = split_fragments(text)
    results: list[ParsedReference] = []
    if not fragments:
        return results

    own_client = http_client is None
    client = http_client or httpx.AsyncClient(timeout=10.0)

    async def _doi(doi: str) -> ArticleMetadata | None:
        if doi_resolver:
            return await doi_resolver(doi)
        return await lookup_doi_metadata(doi, http_client=client, email=email)

    async def _pmid(pmids: list[str]) -> list[ArticleMetadata]:
        if pmid_resolver:
            return await pmid_resolver(pmids)
        return await fetch_pmid_metadata(
            pmids, api_key=api_key, email=email, http_client=client
        )

    async def _title(query: str) -> ArticleMetadata | None:
        if title_resolver:
            return await title_resolver(query)
        if not fuzzy_title_lookup:
            return None
        return await crossref_search_by_title(
            query, http_client=client, email=email
        )

    try:
        for raw in fragments:
            ref = ParsedReference(raw=raw)
            doi = extract_doi(raw)
            pmid = extract_pmid(raw)
            ref.doi = doi
            ref.pmid = pmid

            meta: ArticleMetadata | None = None
            if doi:
                meta = await _doi(doi)
                if meta is None:
                    ref.notes.append(f"Crossref lookup failed for DOI {doi!r}")
            if meta is None and pmid:
                pmid_results = await _pmid([pmid])
                if pmid_results:
                    meta = pmid_results[0]
                else:
                    ref.notes.append(f"PubMed lookup failed for PMID {pmid!r}")
            if meta is None and not doi and not pmid:
                # Use the first 200 chars as the fuzzy-search query — enough
                # to capture the title without sending the full reference.
                query = raw[:200]
                meta = await _title(query)
                if meta is None:
                    ref.notes.append("No high-confidence Crossref title match")

            if meta is not None:
                ref.parsed_metadata = meta
                ref.status = "ok"
                # Surface the DOI / PMID the resolver returned even if the
                # input didn't have them — saves the next dedup pass work.
                if not ref.doi and meta.doi:
                    ref.doi = meta.doi
                if not ref.pmid and meta.pmid:
                    ref.pmid = meta.pmid
            results.append(ref)
    finally:
        if own_client:
            await client.aclose()
    return results


__all__ = [
    "ParsedReference",
    "parse_citation_text",
    "split_fragments",
    "extract_doi",
    "extract_pmid",
    "crossref_search_by_title",
]
