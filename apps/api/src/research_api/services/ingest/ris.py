"""Pure RIS parser → list[ArticleMetadata].

RIS is line-based: ``TAG  - VALUE``. Records terminate with ``ER  -``.
We accept Windows / Unix / mixed line endings via splitlines().
"""
from __future__ import annotations

import logging
import re
from typing import Optional

from ...schemas.ingest import ArticleMetadata

logger = logging.getLogger("research_api.ingest.ris")

# Pattern: TAG (2 chars) + two spaces + "-" + space + VALUE
_LINE_RE = re.compile(r"^([A-Z][A-Z0-9])\s{1,2}-\s?(.*)$")
_TITLE_TAGS = ("TI", "T1")
_AUTHOR_TAGS = ("AU", "A1")
_JOURNAL_TAGS = ("JO", "JF", "T2", "JT")
_YEAR_TAGS = ("PY", "Y1", "DA")
_ABSTRACT_TAGS = ("AB", "N2")


def _normalise_author(raw: str) -> str:
    """Convert ``"Last, First"`` → ``"First Last"`` if a comma is present."""
    raw = raw.strip()
    if "," in raw:
        last, _, rest = raw.partition(",")
        return f"{rest.strip()} {last.strip()}".strip()
    return raw


def _extract_year(raw: str) -> int | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    # First four digits anywhere at the start of the value
    m = re.match(r"\D*(\d{4})", raw)
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None


def parse_ris(text: str) -> list[ArticleMetadata]:
    """Parse RIS text into ArticleMetadata. Skips records lacking a title.

    Never raises — malformed records are silently dropped.
    """
    if not text or not text.strip():
        return []

    records: list[ArticleMetadata] = []
    current: dict[str, list[str]] = {}

    def _flush() -> None:
        nonlocal current
        if not current:
            return
        title = " ".join(current.get("__title__", [])).strip()
        if not title:
            current = {}
            return
        authors = [_normalise_author(a) for a in current.get("__authors__", [])]
        journal = " ".join(current.get("__journal__", [])).strip() or None
        year = _extract_year(" ".join(current.get("__year__", [])))
        volume = " ".join(current.get("VL", [])).strip() or None
        issue = " ".join(current.get("IS", [])).strip() or None
        sp = " ".join(current.get("SP", [])).strip() or None
        ep = " ".join(current.get("EP", [])).strip() or None
        if sp and ep:
            pages: str | None = f"{sp}-{ep}"
        else:
            pages = sp or ep
        doi = " ".join(current.get("DO", [])).strip() or None
        abstract = " ".join(current.get("__abstract__", [])).strip() or None
        records.append(
            ArticleMetadata(
                title=title,
                authors=authors,
                journal=journal,
                year=year,
                volume=volume,
                issue=issue,
                pages=pages,
                doi=doi,
                pmid=None,
                abstract=abstract,
                source="ris",
            )
        )
        current = {}

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line:
            continue
        m = _LINE_RE.match(line)
        if not m:
            continue
        tag, value = m.group(1), m.group(2).strip()
        if tag == "ER":
            _flush()
            continue
        if tag in _TITLE_TAGS:
            current.setdefault("__title__", []).append(value)
        elif tag in _AUTHOR_TAGS:
            if value:
                current.setdefault("__authors__", []).append(value)
        elif tag in _JOURNAL_TAGS:
            # Prefer first journal tag encountered (typically JT/JO over TA)
            current.setdefault("__journal__", []).append(value)
        elif tag in _YEAR_TAGS:
            current.setdefault("__year__", []).append(value)
        elif tag in _ABSTRACT_TAGS:
            current.setdefault("__abstract__", []).append(value)
        else:
            current.setdefault(tag, []).append(value)

    # In case the file ended without a terminating ER tag, still flush.
    _flush()
    return records


__all__ = ["parse_ris"]
