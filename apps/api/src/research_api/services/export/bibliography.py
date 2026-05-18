"""Bibliography assembly: dedupe + ordering of citation tokens.

Walks manuscript sections in canonical order, extracts every cited article
id (from both plain-text `[CITE_xxx]` tokens AND inline `<sup data-citation
data-article-id="...">` markers), deduplicates preserving first-occurrence
order, and renders each in the requested citation style.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Mapping, Protocol

from ..citation_format import CitationStyle, bibliography_entry

# Styles that order the reference list alphabetically by first author's
# surname (case-insensitive). Numbered styles (Vancouver, IEEE) keep their
# existing first-citation-of-appearance policy.
_ALPHABETICAL_STYLES: frozenset[CitationStyle] = frozenset({"apa", "harvard"})

CANONICAL_SECTION_ORDER: tuple[str, ...] = (
    "Abstract",
    "Introduction",
    "Methodology",
    "Results",
    "Discussion",
    "Conclusion",
)

# Capture either `[CITE_xxx]` or `data-article-id="xxx"` in one regex so a
# single pass yields ids in their natural left-to-right order regardless of
# which form the citation took. Both groups share the same id alphabet.
_CITE_OR_ATTR = re.compile(
    r'\[CITE_([A-Za-z0-9_-]+)\]|data-article-id="([A-Za-z0-9_-]+)"'
)


@dataclass(frozen=True)
class BibliographyEntry:
    article_id: str
    number: int
    formatted: str


class _SectionLike(Protocol):
    section_name: str
    content: str


class _ArticleLike(Protocol):
    title: str | None
    authors: list[str]
    year: int | None
    journal: str | None
    doi: str | None


def _ordered_sections(sections: Iterable[_SectionLike]) -> list[_SectionLike]:
    by_name: dict[str, _SectionLike] = {}
    for s in sections:
        by_name[s.section_name] = s
    return [by_name[n] for n in CANONICAL_SECTION_ORDER if n in by_name]


def collect_used_article_ids_in_order(
    sections: Iterable[_SectionLike],
) -> list[str]:
    """Return article ids cited across `sections`, deduplicated, in
    first-occurrence order. Sections are walked in canonical order
    (Abstract → Conclusion) regardless of their input order.
    """
    seen: list[str] = []
    seen_set: set[str] = set()
    for s in _ordered_sections(sections):
        for m in _CITE_OR_ATTR.finditer(s.content or ""):
            aid = m.group(1) or m.group(2)
            if not aid or aid in seen_set:
                continue
            seen.append(aid)
            seen_set.add(aid)
    return seen


def _first_author_surname(article: _ArticleLike) -> str:
    """Lowercased surname of the first author for alphabetical ordering.

    Mirrors `citation_format._surname` (last whitespace token) but returns
    the empty string for articles with no authors so they bucket consistently.
    """
    authors = list(article.authors or [])
    if not authors:
        return ""
    first = (authors[0] or "").strip()
    if not first:
        return ""
    return first.split()[-1].lower()


def _alphabetical_sort_key(
    article: _ArticleLike, *, fallback_position: int
) -> tuple[str, int, str, int]:
    """Sort key: (surname, year, title, fallback_position).

    `fallback_position` is the first-citation index — used to stabilise the
    sort when surname/year/title all tie (genuinely identical metadata
    shouldn't happen, but the secondary key keeps the order deterministic).

    Missing year sorts AFTER any concrete year by using a sentinel
    `10**6` value (year 1,000,000 — outliers don't exist in our corpus).
    """
    surname = _first_author_surname(article)
    year = article.year if article.year is not None else 10**6
    title = (article.title or "").lower()
    return (surname, year, title, fallback_position)


def build_bibliography(
    *,
    articles_by_id: Mapping[str, _ArticleLike],
    sections: Iterable[_SectionLike],
    style: CitationStyle,
) -> list[BibliographyEntry]:
    """Compose `collect_used_article_ids_in_order` + per-style entry rendering.

    Per-style ordering policy:
    - Vancouver / IEEE: first-citation-of-appearance (inline numbers match).
    - APA / Harvard: alphabetical by first author's surname (case-insensitive),
      ties broken by year ASC then title ASC. Inline format is author-year so
      this re-order does not require renumbering inline citations.

    Article ids referenced by manuscript content but absent from
    `articles_by_id` are dropped silently — the integrity panel is the
    user-visible surface for orphan tokens.
    """
    ids = collect_used_article_ids_in_order(sections)

    if style in _ALPHABETICAL_STYLES:
        # Sort by (surname, year, title) but only across articles we have
        # metadata for. Missing-metadata ids are still dropped.
        resolvable: list[tuple[str, _ArticleLike, int]] = []
        for pos, aid in enumerate(ids):
            article = articles_by_id.get(aid)
            if article is None:
                continue
            resolvable.append((aid, article, pos))
        resolvable.sort(
            key=lambda triple: _alphabetical_sort_key(
                triple[1], fallback_position=triple[2],
            )
        )
        out: list[BibliographyEntry] = []
        next_number = 1
        for aid, article, _pos in resolvable:
            formatted = bibliography_entry(article, number=next_number, style=style)
            out.append(BibliographyEntry(article_id=aid, number=next_number, formatted=formatted))
            next_number += 1
        return out

    # Default: first-citation-of-appearance (Vancouver, IEEE).
    out_v: list[BibliographyEntry] = []
    next_number = 1
    for aid in ids:
        article = articles_by_id.get(aid)
        if article is None:
            continue
        formatted = bibliography_entry(article, number=next_number, style=style)
        out_v.append(BibliographyEntry(article_id=aid, number=next_number, formatted=formatted))
        next_number += 1
    return out_v
