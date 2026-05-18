"""PubMed E-utilities ingest: esearch → list[PMID] → efetch → ArticleMetadata.

Defensive parser — never raises; logs WARNING and returns ``[]`` on any
unexpected condition (5xx, parse error, network error). One automatic
retry on HTTP 429.
"""
from __future__ import annotations

import asyncio
import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

import httpx

from ...schemas.ingest import ArticleMetadata

logger = logging.getLogger("research_api.ingest.pubmed")

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

_DEFAULT_TIMEOUT = 15.0
_DEFAULT_EMAIL = "noreply@research-assistant.local"


@dataclass
class PubMedFilters:
    """Optional filter knobs the route layer can pass through to esearch."""

    date_from: str | None = None  # YYYY or YYYY/MM/DD
    date_to: str | None = None
    article_types: list[str] = field(default_factory=list)
    english_only: bool = False


def _shared_params(*, email: str, api_key: str | None) -> dict[str, str]:
    params: dict[str, str] = {
        "db": "pubmed",
        "retmode": "xml",
        "email": email,
        "tool": "ResearchManuscriptAssistant",
    }
    if api_key:
        params["api_key"] = api_key
    return params


def build_esearch_term(query: str, filters: PubMedFilters | None) -> str:
    """Compose a PubMed `term=` query string with optional [dp]/[pt]/[lang] qualifiers.

    Pure function — exported so tests can pin the exact composition.
    """
    base = (query or "").strip()
    if filters is None:
        return base
    parts: list[str] = [base] if base else []
    if filters.date_from or filters.date_to:
        d_from = (filters.date_from or "1800").strip()
        d_to = (filters.date_to or "3000").strip()
        parts.append(f"({d_from}[dp] : {d_to}[dp])")
    if filters.article_types:
        ors = " OR ".join(
            f'"{t.strip()}"[pt]' for t in filters.article_types if t.strip()
        )
        if ors:
            parts.append(f"({ors})")
    if filters.english_only:
        parts.append("english[lang]")
    return " AND ".join(p for p in parts if p)


async def _get_with_retry(
    client: httpx.AsyncClient,
    url: str,
    params: dict[str, str],
    *,
    retry_sleep: float = 1.0,
) -> httpx.Response | None:
    try:
        r = await client.get(url, params=params)
    except httpx.HTTPError as exc:
        logger.warning("pubmed network error: %s", exc)
        return None
    if r.status_code == 429:
        await asyncio.sleep(retry_sleep)
        try:
            r = await client.get(url, params=params)
        except httpx.HTTPError as exc:
            logger.warning("pubmed retry network error: %s", exc)
            return None
        if r.status_code != 200:
            logger.warning("pubmed retried-still-failed: %s", r.status_code)
            return None
        return r
    if r.status_code != 200:
        logger.warning("pubmed non-200: %s", r.status_code)
        return None
    return r


async def search_pubmed(
    query: str,
    *,
    retmax: int = 50,
    sort: str = "relevance",
    filters: PubMedFilters | None = None,
    api_key: str | None = None,
    email: str = _DEFAULT_EMAIL,
    http_client: httpx.AsyncClient | None = None,
    retry_sleep: float = 1.0,
) -> list[ArticleMetadata]:
    """esearch → list of PMIDs → efetch → parse XML → list[ArticleMetadata].

    Empty list on any failure; never raises.
    """
    q = (query or "").strip()
    if not q:
        return []

    own = http_client is None
    client = http_client or httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT)
    try:
        params = _shared_params(email=email, api_key=api_key)
        params["term"] = build_esearch_term(q, filters)
        params["retmax"] = str(retmax)
        if sort:
            params["sort"] = sort
        r = await _get_with_retry(
            client, ESEARCH_URL, params, retry_sleep=retry_sleep
        )
        if r is None:
            return []
        pmids = _parse_esearch_pmids(r.text)
        if not pmids:
            return []
        return await fetch_pmid_metadata(
            pmids,
            api_key=api_key,
            email=email,
            http_client=client,
            retry_sleep=retry_sleep,
        )
    finally:
        if own:
            await client.aclose()


async def fetch_pmid_metadata(
    pmids: list[str],
    *,
    api_key: str | None = None,
    email: str = _DEFAULT_EMAIL,
    http_client: httpx.AsyncClient | None = None,
    retry_sleep: float = 1.0,
) -> list[ArticleMetadata]:
    """Direct efetch path: batch the PMIDs into a single efetch call."""
    if not pmids:
        return []
    own = http_client is None
    client = http_client or httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT)
    try:
        params = _shared_params(email=email, api_key=api_key)
        params["id"] = ",".join(pmids)
        r = await _get_with_retry(
            client, EFETCH_URL, params, retry_sleep=retry_sleep
        )
        if r is None:
            return []
        try:
            return _parse_efetch(r.text)
        except ET.ParseError as exc:
            logger.warning("pubmed efetch XML parse error: %s", exc)
            return []
    finally:
        if own:
            await client.aclose()


# ─── XML parsing ────────────────────────────────────────────────────────────


def _parse_esearch_pmids(text: str) -> list[str]:
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        logger.warning("pubmed esearch XML parse error: %s", exc)
        return []
    return [el.text or "" for el in root.iter("Id") if el.text]


def _parse_efetch(text: str) -> list[ArticleMetadata]:
    root = ET.fromstring(text)
    return [_parse_article(art) for art in root.iter("PubmedArticle")]


def _parse_article(article: ET.Element) -> ArticleMetadata:
    pmid = _findtext(article, "MedlineCitation/PMID")
    title = (
        _findtext(article, "MedlineCitation/Article/ArticleTitle") or "Untitled"
    )
    # Pagination
    pages = _findtext(article, "MedlineCitation/Article/Pagination/MedlinePgn")
    # Journal info
    journal = _findtext(article, "MedlineCitation/Article/Journal/Title")
    issue_el = article.find(
        "MedlineCitation/Article/Journal/JournalIssue"
    )
    volume = (
        _findtext(issue_el, "Volume") if issue_el is not None else None
    )
    issue = _findtext(issue_el, "Issue") if issue_el is not None else None

    year: int | None = None
    if issue_el is not None:
        pubdate = issue_el.find("PubDate")
        if pubdate is not None:
            year_text = _findtext(pubdate, "Year")
            if year_text:
                try:
                    year = int(year_text)
                except ValueError:
                    year = None
            else:
                medline_date = _findtext(pubdate, "MedlineDate") or ""
                if medline_date[:4].isdigit():
                    year = int(medline_date[:4])

    # Authors — skip CollectiveName-only entries
    authors: list[str] = []
    affiliations: list[str] = []
    seen_affiliations: set[str] = set()
    for author in article.iter("Author"):
        last = _findtext(author, "LastName") or ""
        fore = _findtext(author, "ForeName") or ""
        full = f"{fore} {last}".strip()
        if full:
            authors.append(full)
        # Affiliations: any AffiliationInfo/Affiliation under this author.
        # Collect at the article level (deduped, order-preserving).
        for aff in author.iter("Affiliation"):
            text = (aff.text or "").strip()
            if text and text not in seen_affiliations:
                seen_affiliations.add(text)
                affiliations.append(text)

    # Abstract — join multi-segment AbstractText. Prefer label-prefixed form
    # whenever the segment carries a Label attribute.
    abstract_parts: list[str] = []
    for el in article.iter("AbstractText"):
        segment = (el.text or "").strip()
        if not segment:
            continue
        label = el.get("Label")
        abstract_parts.append(f"{label}: {segment}" if label else segment)
    abstract = " ".join(abstract_parts) if abstract_parts else None

    # MeSH descriptor terms
    mesh_terms: list[str] = []
    for desc in article.iter("DescriptorName"):
        t = (desc.text or "").strip()
        if t:
            mesh_terms.append(t)

    # Publication types
    article_types: list[str] = []
    for pt in article.iter("PublicationType"):
        t = (pt.text or "").strip()
        if t and t not in article_types:
            article_types.append(t)

    # DOI from ArticleIdList
    doi: str | None = None
    for aid in article.iter("ArticleId"):
        if (aid.get("IdType") or "").lower() == "doi":
            doi = (aid.text or "").strip() or None
            break

    return ArticleMetadata(
        title=title.strip(),
        authors=authors,
        journal=journal,
        year=year,
        volume=volume,
        issue=issue,
        pages=pages,
        doi=doi,
        pmid=pmid,
        abstract=abstract,
        source="pubmed",
        mesh_terms=mesh_terms,
        affiliations=affiliations,
        article_types=article_types,
    )


def _findtext(el: ET.Element | None, path: str) -> str | None:
    if el is None:
        return None
    found = el.find(path)
    if found is None or found.text is None:
        return None
    return found.text.strip() or None


__all__ = [
    "ESEARCH_URL",
    "EFETCH_URL",
    "PubMedFilters",
    "build_esearch_term",
    "search_pubmed",
    "fetch_pmid_metadata",
]
