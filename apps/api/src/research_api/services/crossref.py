"""CrossRef DOI lookup — authoritative metadata source as fallback to AI extraction.

Returns None on any failure (404, network, parse). Caller falls through to AI result.
"""
from __future__ import annotations

import re

import httpx

from .ai.schemas import CitationMetadata

_DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$")
CROSSREF_BASE = "https://api.crossref.org/works"


def normalise_doi(doi: str) -> str | None:
    """Strip common prefixes and validate against the DOI pattern."""
    if not doi:
        return None
    s = doi.strip()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:", "DOI:"):
        if s.startswith(prefix):
            s = s[len(prefix) :]
            break
    s = s.strip().rstrip(".)")
    return s if _DOI_RE.match(s) else None


async def lookup_doi(
    doi: str, *, http_client: httpx.AsyncClient | None = None, timeout: float = 10.0
) -> CitationMetadata | None:
    """Fetch CrossRef metadata for a DOI. Returns None on any failure."""
    clean = normalise_doi(doi)
    if not clean:
        return None

    own_client = http_client is None
    client = http_client or httpx.AsyncClient(timeout=timeout)
    try:
        r = await client.get(
            f"{CROSSREF_BASE}/{clean}",
            headers={"User-Agent": "ResearchManuscriptAssistant/0.0.1 (mailto:noreply@local)"},
        )
        if r.status_code != 200:
            return None
        message = r.json().get("message")
        if not message:
            return None
        return _from_crossref_message(message, clean)
    except (httpx.HTTPError, ValueError, KeyError):
        return None
    finally:
        if own_client:
            await client.aclose()


def _from_crossref_message(msg: dict, doi: str) -> CitationMetadata:
    title = (msg.get("title") or ["UNKNOWN"])[0]
    authors = [
        f"{a.get('given', '').strip()} {a.get('family', '').strip()}".strip()
        for a in (msg.get("author") or [])
        if a.get("given") or a.get("family")
    ]
    journal = (msg.get("container-title") or [None])[0]
    year = None
    issued = msg.get("issued", {}).get("date-parts") or msg.get("published-print", {}).get(
        "date-parts"
    )
    if issued and issued[0]:
        year = int(issued[0][0])
    return CitationMetadata(
        title=title,
        authors=authors,
        journal=journal,
        year=year,
        volume=msg.get("volume"),
        issue=msg.get("issue"),
        pages=msg.get("page"),
        doi=doi,
        confidence=1.0,
    )
