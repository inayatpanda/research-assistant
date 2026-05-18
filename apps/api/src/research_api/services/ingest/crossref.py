"""DOI → ArticleMetadata via Crossref.

Thin wrapper around ``services.crossref.lookup_doi`` that also pulls the
JATS abstract (when present), strips JATS tags, and emits the uniform
``ArticleMetadata(source='doi')`` shape used by every ingest surface.
"""
from __future__ import annotations

import logging
import re
from urllib.parse import quote

import httpx

from ...schemas.ingest import ArticleMetadata
from ..crossref import CROSSREF_BASE, normalise_doi

logger = logging.getLogger("research_api.ingest.crossref")

_JATS_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")


def _strip_jats(raw: str | None) -> str | None:
    if not raw:
        return None
    cleaned = _JATS_TAG.sub(" ", raw)
    cleaned = _WS.sub(" ", cleaned).strip()
    return cleaned or None


async def lookup_doi_metadata(
    doi: str,
    *,
    http_client: httpx.AsyncClient | None = None,
    timeout: float = 10.0,
    email: str = "noreply@research-assistant.local",
) -> ArticleMetadata | None:
    """Resolve a DOI via Crossref → uniform ArticleMetadata.

    Returns ``None`` on 404 / parse failure / network error / malformed DOI.
    """
    clean = normalise_doi(doi)
    if not clean:
        return None

    own_client = http_client is None
    client = http_client or httpx.AsyncClient(timeout=timeout)
    encoded = quote(clean, safe="/")
    try:
        r = await client.get(
            f"{CROSSREF_BASE}/{encoded}",
            headers={
                "User-Agent": (
                    f"ResearchManuscriptAssistant/0.0.1 (mailto:{email})"
                ),
            },
        )
        if r.status_code != 200:
            return None
        msg = (r.json() or {}).get("message")
        if not msg:
            return None
        return _to_metadata(msg, clean)
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        logger.warning("crossref lookup failed for %s: %s", clean, exc)
        return None
    finally:
        if own_client:
            await client.aclose()


def _to_metadata(msg: dict, doi: str) -> ArticleMetadata:
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
        abstract=_strip_jats(msg.get("abstract")),
        source="doi",
    )
