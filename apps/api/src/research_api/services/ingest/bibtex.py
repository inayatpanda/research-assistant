"""BibTeX parser → list[ArticleMetadata] via bibtexparser v1.

Only ``@article`` entries are returned — other entry types (book,
inproceedings, etc.) are silently skipped, reflecting the journal-only
focus of this app's manuscript pipeline.
"""
from __future__ import annotations

import logging
import re

from ...schemas.ingest import ArticleMetadata

logger = logging.getLogger("research_api.ingest.bibtex")

_BRACE_ARMOR_RE = re.compile(r"[{}]")
_WS_RE = re.compile(r"\s+")


def _strip_braces(s: str | None) -> str | None:
    if s is None:
        return None
    cleaned = _BRACE_ARMOR_RE.sub("", s)
    cleaned = _WS_RE.sub(" ", cleaned).strip()
    return cleaned or None


def _normalise_author(raw: str) -> str:
    raw = _strip_braces(raw) or ""
    if "," in raw:
        last, _, rest = raw.partition(",")
        return f"{rest.strip()} {last.strip()}".strip()
    return raw.strip()


def _split_authors(raw: str | None) -> list[str]:
    if not raw:
        return []
    # BibTeX uses ' and ' as the author separator.
    parts = re.split(r"\s+and\s+", raw)
    return [a for a in (_normalise_author(p) for p in parts) if a]


def _extract_year(raw: str | None) -> int | None:
    if not raw:
        return None
    m = re.search(r"(\d{4})", raw)
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None


def _canonical_pages(raw: str | None) -> str | None:
    if not raw:
        return None
    return _strip_braces(raw.replace("--", "-"))


def parse_bibtex(text: str) -> list[ArticleMetadata]:
    """Parse BibTeX text via bibtexparser v1.

    Only ``@article`` entries returned. Never raises — any parser error
    yields an empty list and emits a WARNING log line.
    """
    if not text or not text.strip():
        return []

    try:
        import bibtexparser  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - dep is in pyproject
        logger.warning("bibtexparser not importable: %s", exc)
        return []

    try:
        db = bibtexparser.loads(text)
    except Exception as exc:  # bibtexparser raises a variety of types
        logger.warning("bibtexparser parse error: %s", exc)
        return []

    records: list[ArticleMetadata] = []
    for entry in getattr(db, "entries", []) or []:
        etype = (entry.get("ENTRYTYPE") or "").strip().lower()
        if etype != "article":
            continue
        title = _strip_braces(entry.get("title"))
        if not title:
            continue
        records.append(
            ArticleMetadata(
                title=title,
                authors=_split_authors(entry.get("author")),
                journal=_strip_braces(
                    entry.get("journal") or entry.get("journaltitle")
                ),
                year=_extract_year(entry.get("year")),
                volume=_strip_braces(entry.get("volume")),
                issue=_strip_braces(entry.get("number") or entry.get("issue")),
                pages=_canonical_pages(entry.get("pages")),
                doi=_strip_braces(entry.get("doi")),
                pmid=None,
                abstract=_strip_braces(entry.get("abstract")),
                source="bibtex",
            )
        )
    return records


__all__ = ["parse_bibtex"]
