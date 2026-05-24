"""F1 — PDF metadata autofill (Crossref-first, heuristics-fallback).

Pure functions, no I/O except the Crossref HTTP call delegated to the
existing ``services.ingest.crossref.lookup_doi_metadata`` helper. Designed
so each piece can be unit-tested in isolation without mocking anything but
the network call.

Pipeline:
    pdf_bytes
        -> extract_first_pages_text (existing pypdf helper)
        -> extract_doi_from_text  (regex over the first ~5 pages)
        -> if DOI:  enrich_via_crossref(doi)        -> status = "doi_match"
           else:    extract_heuristic_metadata(txt) -> status = "heuristic_only"
        -> if both empty: status = "failed"

Every field that came back gets stamped in the returned ``provenance`` map
so the upload route can decide what to write to the database and the
frontend can render an "autofilled by …" pill next to the field.
"""
from __future__ import annotations

import logging
import re
from typing import Any

from ..pdf_text import extract_first_pages_text
from .crossref import lookup_doi_metadata

logger = logging.getLogger("research_api.ingest.pdf_metadata")

# Greedy enough to catch real-world DOIs (which include unusual punctuation
# like ``/`` and ``.``) but stops at whitespace and the four bracket-style
# characters that almost always close an inline citation.
_DOI_RE = re.compile(r"10\.\d{4,9}/[^\s\]\)>]+", re.IGNORECASE)

# Strip trailing punctuation that almost always belongs to the surrounding
# prose rather than the DOI itself (``.``, ``,``, ``;`` …).
_TRAILING_PUNCT = ".,;:()[]{}"

_YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2})\b")

_AFFILIATION_KEYWORDS = (
    "university",
    "department",
    "institute",
    "school of",
    "faculty",
    "hospital",
)


def _looks_like_affiliation(line: str) -> bool:
    low = line.lower()
    if any(kw in low for kw in _AFFILIATION_KEYWORDS):
        return True
    # A leading street number is a giveaway too.
    return bool(re.search(r"\b\d{2,}\s+\w+", line))


def _sanitise_doi(raw: str) -> str:
    s = raw.strip()
    # Drop matched-bracket pairs that the regex couldn't see (e.g.
    # ``10.1234/foo(bar)`` is legal, but ``(10.1234/foo)`` should yield
    # ``10.1234/foo``). We only strip *trailing* runs of these chars.
    while s and s[-1] in _TRAILING_PUNCT:
        s = s[:-1]
    return s


def extract_doi_from_text(text: str) -> str | None:
    """Find the first DOI-looking substring in ``text``.

    Returns ``None`` when no DOI candidate is present. The returned string
    is sanitised (no trailing punctuation, no surrounding whitespace) but
    not validated against the canonical DOI grammar — that is the job of
    ``crossref.normalise_doi`` downstream.
    """
    if not text:
        return None
    m = _DOI_RE.search(text)
    if not m:
        return None
    return _sanitise_doi(m.group(0)) or None


def extract_heuristic_metadata(text: str) -> dict[str, Any]:
    """Best-effort title / authors / year from raw PDF text.

    Strategy mirrors what a human eye does on the first page:
      - title  = first non-empty line of 5–15 words
      - authors = next non-empty line, split on commas / "and" / "&" /
        semicolons (tolerant — many PDFs format authors weirdly)
      - year = first four-digit year found anywhere in the text

    Any field we cannot infer is omitted from the returned dict so the
    caller can distinguish "absent" from "explicitly None".
    """
    out: dict[str, Any] = {}
    if not text:
        return out

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    title_idx: int | None = None
    for i, line in enumerate(lines):
        wc = len(line.split())
        if 5 <= wc <= 15:
            out["title"] = line
            title_idx = i
            break

    if title_idx is not None and title_idx + 1 < len(lines):
        author_line = lines[title_idx + 1]
        # Affiliation lines almost always contain digits, "University",
        # "Department", "Institute", or "School" — skip those outright so
        # we don't pollute the authors list with addresses.
        if not _looks_like_affiliation(author_line):
            # Split on common author separators; tolerate "and" / "&"
            parts = re.split(r"\s*(?:,| and | & |;)\s*", author_line)
            authors = [p.strip() for p in parts if p.strip()]
            if authors and all(len(a) < 60 for a in authors):
                out["authors"] = authors

    year_match = _YEAR_RE.search(text)
    if year_match:
        try:
            out["year"] = int(year_match.group(1))
        except ValueError:
            pass

    return out


async def enrich_via_crossref(doi: str) -> dict[str, Any] | None:
    """Resolve a DOI through the existing Crossref helper.

    Returns the standard metadata dict, or ``None`` on miss / network
    failure (matching ``lookup_doi_metadata``'s contract).
    """
    meta = await lookup_doi_metadata(doi)
    if meta is None:
        return None
    return {
        "title": meta.title,
        "authors": list(meta.authors or []),
        "journal": meta.journal,
        "year": meta.year,
        "volume": meta.volume,
        "issue": meta.issue,
        "pages": meta.pages,
        "abstract": meta.abstract,
        "doi": meta.doi,
    }


async def extract_metadata_for_pdf(pdf_bytes: bytes) -> dict[str, Any]:
    """Top-level orchestrator. Always returns a dict — never raises.

    Shape::

        {
            "fields":      {<bibliographic-fields-with-non-empty-values>},
            "provenance":  {<field> -> "doi" | "heuristic">},
            "autofill_status": "doi_match" | "heuristic_only" | "failed",
            "doi_candidate": <raw DOI string or None>,
        }
    """
    text = ""
    try:
        text = extract_first_pages_text(pdf_bytes, n=5)
    except Exception:
        logger.exception("pdf_metadata: text extraction crashed")

    doi = extract_doi_from_text(text) if text else None

    # 1) Crossref (preferred)
    if doi:
        try:
            cr = await enrich_via_crossref(doi)
        except Exception:
            logger.exception("pdf_metadata: enrich_via_crossref crashed")
            cr = None
        if cr:
            fields = {k: v for k, v in cr.items() if _is_present(v)}
            return {
                "fields": fields,
                "provenance": {k: "doi" for k in fields},
                "autofill_status": "doi_match",
                "doi_candidate": doi,
            }

    # 2) Heuristics fallback (also runs if the Crossref call missed/failed)
    heur = extract_heuristic_metadata(text)
    # Keep the DOI even if Crossref didn't resolve — saves the user a step
    # if they want to retry "Add by DOI" manually.
    if doi and "doi" not in heur:
        heur["doi"] = doi
    fields = {k: v for k, v in heur.items() if _is_present(v)}

    if not fields:
        return {
            "fields": {},
            "provenance": {},
            "autofill_status": "failed",
            "doi_candidate": doi,
        }
    return {
        "fields": fields,
        "provenance": {k: "heuristic" for k in fields},
        "autofill_status": "heuristic_only",
        "doi_candidate": doi,
    }


def _is_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str) and not value.strip():
        return False
    if isinstance(value, list) and not value:
        return False
    return True
