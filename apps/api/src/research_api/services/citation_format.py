"""Inline-citation formatting + CITE-token replacement.

This module is the **trust boundary** for citations: every formatted citation
that appears in user-facing text is built here from authoritative `articles`
metadata, never from AI model output. AI generations contain placeholder
tokens like `[CITE_a1]` which this module replaces.
"""
from __future__ import annotations

import re
from typing import Literal, Mapping, Protocol

CitationStyle = Literal["vancouver", "apa", "harvard"]
_CITE_RE = re.compile(r"\[CITE_([A-Za-z0-9_-]+)\]")


class _ArticleLike(Protocol):
    title: str | None
    authors: list[str]
    year: int | None
    journal: str | None
    doi: str | None


def _surname(name: str) -> str:
    """Best-effort surname extraction: last whitespace-separated token."""
    parts = (name or "").strip().split()
    return parts[-1] if parts else (name or "").strip()


def vancouver_inline(article: _ArticleLike) -> str:
    """Author-year inline citation in Vancouver style.

    1 author  → 'Doe, 2024'
    2 authors → 'Doe & Smith, 2024'
    3+        → 'Doe et al., 2024'
    No year   → 'Doe et al., n.d.'
    No data   → 'Unknown source'
    """
    authors = article.authors or []
    year = article.year
    year_str = str(year) if year else "n.d."
    if not authors:
        return f"Unknown source, {year_str}" if year else "Unknown source"
    surnames = [_surname(a) for a in authors if _surname(a)]
    if not surnames:
        return f"Unknown source, {year_str}" if year else "Unknown source"
    if len(surnames) == 1:
        return f"{surnames[0]}, {year_str}"
    if len(surnames) == 2:
        return f"{surnames[0]} & {surnames[1]}, {year_str}"
    return f"{surnames[0]} et al., {year_str}"


# APA and Harvard inline format match Vancouver inline for v1.
# Full bibliography differences land in Phase 8.
apa_inline = vancouver_inline
harvard_inline = vancouver_inline


_FORMATTERS: dict[CitationStyle, callable] = {
    "vancouver": vancouver_inline,
    "apa": apa_inline,
    "harvard": harvard_inline,
}


def format_inline(style: CitationStyle, article: _ArticleLike) -> str:
    return _FORMATTERS[style](article)


def tag_for_index(n: int) -> str:
    """Stable, model-friendly tag for the n-th card (1-based)."""
    return f"a{n}"


def replace_cite_tokens(
    text: str,
    articles_by_tag: Mapping[str, _ArticleLike],
    *,
    style: CitationStyle = "vancouver",
) -> str:
    """Replace `[CITE_xxx]` tokens with formatted `(Author et al., Year)`.

    Unknown tags (model hallucinated) are LEFT UNTOUCHED so reviewers see
    the broken reference rather than silently swallow it.
    """
    def sub(m: re.Match[str]) -> str:
        tag = m.group(1)
        article = articles_by_tag.get(tag)
        if article is None:
            return m.group(0)
        return f"({format_inline(style, article)})"

    return _CITE_RE.sub(sub, text)


def _author_list_vancouver(authors: list[str]) -> str:
    """Vancouver: 'Last F, Last F, et al.' Authors as 'First Last' input."""
    if not authors:
        return "Anonymous"
    formatted: list[str] = []
    for a in authors[:6]:
        parts = (a or "").strip().split()
        if not parts:
            continue
        last = parts[-1]
        initials = "".join(p[0].upper() for p in parts[:-1] if p)
        formatted.append(f"{last} {initials}" if initials else last)
    if len(authors) > 6:
        formatted.append("et al.")
    return ", ".join(formatted)


def bibliography_entry(
    article: _ArticleLike, *, number: int | None = None, style: CitationStyle = "vancouver"
) -> str:
    """Single reference-list entry.

    Vancouver: '1. Doe J, Smith J. Anterior approach. J Orthop Res. 2024;42(3):100-110. doi:10.x'

    For v1, APA/Harvard converge with Vancouver. Phase 8 polish adds full fidelity.
    """
    prefix = f"{number}. " if number is not None else ""
    authors = _author_list_vancouver(list(article.authors or []))
    title = (article.title or "Untitled").rstrip(".")
    journal = article.journal or ""
    year = str(article.year) if article.year else "n.d."
    issue_block = ""
    volume = getattr(article, "volume", None)
    issue = getattr(article, "issue", None)
    pages = getattr(article, "pages", None)
    if volume:
        issue_block = f"{volume}"
        if issue:
            issue_block += f"({issue})"
        if pages:
            issue_block += f":{pages}"
    elif pages:
        issue_block = pages
    parts = [f"{prefix}{authors}.", f"{title}."]
    if journal:
        parts.append(f"{journal}.")
    tail = year
    if issue_block:
        tail += f";{issue_block}"
    parts.append(f"{tail}.")
    if article.doi:
        parts.append(f"doi:{article.doi}")
    _ = style
    return " ".join(parts)


def extract_used_citations(
    text: str,
    articles_by_tag: Mapping[str, _ArticleLike],
    *,
    style: CitationStyle = "vancouver",
) -> list[str]:
    """Return distinct formatted citations actually referenced in `text`."""
    seen: list[str] = []
    for m in _CITE_RE.finditer(text):
        article = articles_by_tag.get(m.group(1))
        if article is None:
            continue
        formatted = format_inline(style, article)
        if formatted not in seen:
            seen.append(formatted)
    return seen
