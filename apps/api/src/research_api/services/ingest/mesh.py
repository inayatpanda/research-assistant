"""NCBI MeSH descriptor lookup (Phase 19 / MP19).

Thin wrapper around NCBI E-utilities for ``db=mesh``:
  * ``search_mesh(term)`` → esearch returns descriptor UIDs.
  * ``fetch_mesh(uids)``  → efetch returns XML; parser extracts UI, name,
    scope note, tree numbers, entry terms.

Defensive parser — never raises; returns ``[]`` on any failure. Mirrors
``services/ingest/pubmed.py`` so the cache layer / route layer treat
this as a drop-in alongside the existing PubMed wrapper.
"""
from __future__ import annotations

import asyncio
import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass

import httpx

logger = logging.getLogger("research_api.ingest.mesh")

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

_DEFAULT_TIMEOUT = 15.0
_DEFAULT_EMAIL = "noreply@research-assistant.local"


@dataclass(frozen=True)
class MeshDescriptor:
    descriptor_ui: str
    descriptor_name: str
    scope_note: str | None
    tree_numbers: list[str]
    entry_terms: list[str]


def _shared_params(*, email: str, api_key: str | None) -> dict[str, str]:
    params: dict[str, str] = {
        "db": "mesh",
        "retmode": "xml",
        "email": email,
        "tool": "ResearchManuscriptAssistant",
    }
    if api_key:
        params["api_key"] = api_key
    return params


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
        logger.warning("mesh network error: %s", exc)
        return None
    if r.status_code == 429:
        await asyncio.sleep(retry_sleep)
        try:
            r = await client.get(url, params=params)
        except httpx.HTTPError as exc:
            logger.warning("mesh retry network error: %s", exc)
            return None
        if r.status_code != 200:
            logger.warning("mesh retried-still-failed: %s", r.status_code)
            return None
        return r
    if r.status_code != 200:
        logger.warning("mesh non-200: %s", r.status_code)
        return None
    return r


async def search_mesh(
    term: str,
    *,
    retmax: int = 20,
    api_key: str | None = None,
    email: str = _DEFAULT_EMAIL,
    http_client: httpx.AsyncClient | None = None,
    retry_sleep: float = 1.0,
) -> list[MeshDescriptor]:
    """``esearch db=mesh`` → list of MeshDescriptor."""
    q = (term or "").strip()
    if not q:
        return []
    own = http_client is None
    client = http_client or httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT)
    try:
        params = _shared_params(email=email, api_key=api_key)
        params["term"] = q
        params["retmax"] = str(retmax)
        r = await _get_with_retry(
            client, ESEARCH_URL, params, retry_sleep=retry_sleep
        )
        if r is None:
            return []
        uids = _parse_esearch_uids(r.text)
        if not uids:
            return []
        return await fetch_mesh(
            uids,
            api_key=api_key,
            email=email,
            http_client=client,
            retry_sleep=retry_sleep,
        )
    finally:
        if own:
            await client.aclose()


async def fetch_mesh(
    uids: list[str],
    *,
    api_key: str | None = None,
    email: str = _DEFAULT_EMAIL,
    http_client: httpx.AsyncClient | None = None,
    retry_sleep: float = 1.0,
) -> list[MeshDescriptor]:
    """``efetch db=mesh`` → list of MeshDescriptor."""
    if not uids:
        return []
    own = http_client is None
    client = http_client or httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT)
    try:
        params = _shared_params(email=email, api_key=api_key)
        params["id"] = ",".join(uids)
        r = await _get_with_retry(
            client, EFETCH_URL, params, retry_sleep=retry_sleep
        )
        if r is None:
            return []
        try:
            return parse_mesh_xml(r.text)
        except ET.ParseError as exc:
            logger.warning("mesh efetch XML parse error: %s", exc)
            return []
    finally:
        if own:
            await client.aclose()


def _parse_esearch_uids(text: str) -> list[str]:
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        logger.warning("mesh esearch XML parse error: %s", exc)
        return []
    return [el.text or "" for el in root.iter("Id") if el.text]


def parse_mesh_xml(text: str) -> list[MeshDescriptor]:
    """Parse the MeSH XML returned by efetch.

    NCBI returns ``DescriptorRecord`` elements under ``DescriptorRecordSet``.
    Tolerates two known XML shapes:
      - The "MeSH browser" XML used by ``efetch db=mesh``
        (``DescriptorRecordSet/DescriptorRecord``)
      - A lighter ``MeshHeading``-style document used by some E-utility
        responses (``DescriptorRecord`` with ``DescriptorUI``,
        ``DescriptorName/String``).
    Unrecognised structures yield an empty list (defensive).
    """
    root = ET.fromstring(text)
    out: list[MeshDescriptor] = []
    for desc in root.iter("DescriptorRecord"):
        ui = _findtext(desc, "DescriptorUI") or ""
        name = (
            _findtext(desc, "DescriptorName/String")
            or _findtext(desc, "DescriptorName")
            or ""
        )
        scope = (
            _findtext(desc, "ConceptList/Concept/ScopeNote")
            or _findtext(desc, "ScopeNote")
        )
        if scope:
            scope = scope.strip()
        tree_numbers: list[str] = []
        for tn in desc.iter("TreeNumber"):
            t = (tn.text or "").strip()
            if t:
                tree_numbers.append(t)
        entry_terms: list[str] = []
        for term in desc.iter("Term"):
            s = _findtext(term, "String") or (term.text or "")
            s = (s or "").strip()
            if s and s != name and s not in entry_terms:
                entry_terms.append(s)
        if not ui or not name:
            continue
        out.append(
            MeshDescriptor(
                descriptor_ui=ui.strip(),
                descriptor_name=name.strip(),
                scope_note=scope or None,
                tree_numbers=tree_numbers,
                entry_terms=entry_terms,
            )
        )
    return out


def _findtext(el: ET.Element | None, path: str) -> str | None:
    if el is None:
        return None
    found = el.find(path)
    if found is None or found.text is None:
        return None
    return found.text


__all__ = [
    "MeshDescriptor",
    "ESEARCH_URL",
    "EFETCH_URL",
    "search_mesh",
    "fetch_mesh",
    "parse_mesh_xml",
]
