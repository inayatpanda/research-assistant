"""Bibliography assembly: dedupe + ordering of citation tokens.

Walks manuscript sections in canonical order, extracts every cited article
id (from both plain-text `[CITE_xxx]` tokens AND inline `<sup data-citation
data-article-id="...">` markers), deduplicates preserving first-occurrence
order, and renders each in the requested citation style.

Article ids prefixed with `dataset_` resolve against the project's datasets
list (passed via the optional `datasets=` kwarg) and render as a synthetic
"Internal research dataset" entry rather than being treated as orphans.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable, Mapping, Protocol

from ..citation_format import CitationStyle, bibliography_entry

# Styles that order the reference list alphabetically by first author's
# surname (case-insensitive). Numbered styles (Vancouver, IEEE) keep their
# existing first-citation-of-appearance policy.
_ALPHABETICAL_STYLES: frozenset[CitationStyle] = frozenset({"apa", "harvard"})

# Prefix used on `data-article-id` (and `[CITE_…]`) attributes when the cited
# entity is a project dataset rather than a library article. Centralised so a
# rename only touches one constant.
DATASET_CITATION_PREFIX = "dataset_"

# Default authorship rendered on synthetic dataset bibliography entries.
# Plural noun matches the SAP convention ("project investigators conducted…").
DEFAULT_DATASET_AUTHORS: tuple[str, ...] = ("Project investigators",)

# Bibliography "journal" slot for synthetic dataset entries. The square
# brackets are intentional — they make the entry visually distinct in the
# reference list and mirror common citation-style guidance for non-traditional
# sources (e.g. APA's `[Data set]` qualifier).
DATASET_JOURNAL_LABEL = "[Internal research dataset]"

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
    # "article" (library reference) or "dataset" (synthetic dataset entry).
    # Defaulted to "article" so all pre-existing call sites keep the prior
    # serialisation shape.
    type: str = "article"


class _SectionLike(Protocol):
    section_name: str
    content: str


class _ArticleLike(Protocol):
    title: str | None
    authors: list[str]
    year: int | None
    journal: str | None
    doi: str | None


class DatasetLike(Protocol):
    """Subset of the Dataset ORM we depend on for synthetic entries.

    Kept as a Protocol so tests (and any future non-ORM source) can pass a
    simple dataclass instead of constructing a full SQLAlchemy row.
    """
    id: str
    filename: str
    created_at: datetime
    project_id: str
    user_id: str


@dataclass(frozen=True)
class _SyntheticDatasetArticle:
    """Article-shaped adapter rendered by the standard citation_format
    bibliography_entry function — the formatters branch on `type` only when
    they need dataset-specific rendering.
    """
    title: str | None
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    journal: str | None = None
    doi: str | None = None
    volume: str | None = None
    issue: str | None = None
    pages: str | None = None
    type: str = "dataset"


def _dataset_to_article(ds: DatasetLike, *, authors: list[str] | None = None) -> _SyntheticDatasetArticle:
    """Render a Dataset row as an article-shaped object for the formatter."""
    year_val: int | None = None
    created = getattr(ds, "created_at", None)
    if created is not None:
        try:
            year_val = created.year
        except AttributeError:  # pragma: no cover — created_at always datetime-like
            year_val = None
    return _SyntheticDatasetArticle(
        title=ds.filename or "Dataset",
        authors=list(authors or DEFAULT_DATASET_AUTHORS),
        year=year_val,
        journal=DATASET_JOURNAL_LABEL,
    )


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
    datasets: Iterable[DatasetLike] | None = None,
) -> list[BibliographyEntry]:
    """Compose `collect_used_article_ids_in_order` + per-style entry rendering.

    Per-style ordering policy:
    - Vancouver / IEEE: first-citation-of-appearance (inline numbers match).
    - APA / Harvard: alphabetical by first author's surname (case-insensitive),
      ties broken by year ASC then title ASC. Inline format is author-year so
      this re-order does not require renumbering inline citations.

    Article ids referenced by manuscript content but absent from
    `articles_by_id` AND `datasets` are dropped silently — the integrity
    panel is the user-visible surface for orphan tokens.

    When a cited id begins with `dataset_` the suffix is matched against
    `datasets[*].id`; matches render a synthetic "Internal research dataset"
    entry with the dataset filename as title, "Project investigators" as
    author, and the upload year. Unknown dataset ids are also dropped.
    """
    ids = collect_used_article_ids_in_order(sections)
    datasets_by_id: dict[str, DatasetLike] = {d.id: d for d in (datasets or [])}

    def _resolve(aid: str) -> tuple[_ArticleLike, str] | None:
        """Return (article-shaped record, "article"|"dataset") or None."""
        if aid.startswith(DATASET_CITATION_PREFIX):
            ds = datasets_by_id.get(aid[len(DATASET_CITATION_PREFIX):])
            if ds is None:
                return None
            return _dataset_to_article(ds), "dataset"
        art = articles_by_id.get(aid)
        if art is None:
            return None
        return art, "article"

    if style in _ALPHABETICAL_STYLES:
        # Sort by (surname, year, title) but only across ids we can resolve.
        resolvable: list[tuple[str, _ArticleLike, str, int]] = []
        for pos, aid in enumerate(ids):
            resolved = _resolve(aid)
            if resolved is None:
                continue
            article, kind = resolved
            resolvable.append((aid, article, kind, pos))
        resolvable.sort(
            key=lambda quad: _alphabetical_sort_key(
                quad[1], fallback_position=quad[3],
            )
        )
        out: list[BibliographyEntry] = []
        next_number = 1
        for aid, article, kind, _pos in resolvable:
            formatted = bibliography_entry(article, number=next_number, style=style)
            out.append(BibliographyEntry(
                article_id=aid, number=next_number, formatted=formatted, type=kind,
            ))
            next_number += 1
        return out

    # Default: first-citation-of-appearance (Vancouver, IEEE).
    out_v: list[BibliographyEntry] = []
    next_number = 1
    for aid in ids:
        resolved = _resolve(aid)
        if resolved is None:
            continue
        article, kind = resolved
        formatted = bibliography_entry(article, number=next_number, style=style)
        out_v.append(BibliographyEntry(
            article_id=aid, number=next_number, formatted=formatted, type=kind,
        ))
        next_number += 1
    return out_v
