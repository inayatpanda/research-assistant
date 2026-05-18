"""Inline-citation formatting + CITE-token replacement.

This module is the **trust boundary** for citations: every formatted citation
that appears in user-facing text is built here from authoritative `articles`
metadata, never from AI model output. AI generations contain placeholder
tokens like `[CITE_a1]` which this module replaces.
"""
from __future__ import annotations

import re
from html import escape
from typing import Callable, Literal, Mapping, Protocol

CitationStyle = Literal["vancouver", "apa", "harvard", "ieee"]
_CITE_RE = re.compile(r"\[CITE_([A-Za-z0-9_-]+)\]")
_EN_DASH = "–"


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


def _initials(given_parts: list[str]) -> str:
    return "".join(p[0].upper() for p in given_parts if p)


def _initials_dotted(given_parts: list[str]) -> str:
    """APA/Harvard initials: `F. M.` (dot + space after each)."""
    return " ".join(f"{p[0].upper()}." for p in given_parts if p)


def _split_name(name: str) -> tuple[str, list[str]]:
    """Return (surname, given_parts). Surname is last whitespace token."""
    parts = (name or "").strip().split()
    if not parts:
        return "", []
    return parts[-1], parts[:-1]


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
apa_inline = vancouver_inline
harvard_inline = vancouver_inline


def ieee_inline(n: int) -> str:
    """IEEE inline citation: `[N]` — caller supplies the bibliography number."""
    return f"[{n}]"


_INLINE_FORMATTERS: dict[CitationStyle, Callable[[_ArticleLike], str]] = {
    "vancouver": vancouver_inline,
    "apa": apa_inline,
    "harvard": harvard_inline,
    # IEEE inline is number-based — handled via dedicated path; this entry
    # exists so format_inline still answers for compat (returns Vancouver-ish).
    "ieee": vancouver_inline,
}


def format_inline(style: CitationStyle, article: _ArticleLike) -> str:
    if style not in _INLINE_FORMATTERS:
        raise ValueError(f"Unknown citation style: {style!r}")
    return _INLINE_FORMATTERS[style](article)


def tag_for_index(n: int) -> str:
    """Stable, model-friendly tag for the n-th card (1-based)."""
    return f"a{n}"


def replace_cite_tokens(
    text: str,
    articles_by_tag: Mapping[str, _ArticleLike],
    *,
    style: CitationStyle = "vancouver",
    numbering: Mapping[str, int] | None = None,
) -> str:
    """Replace `[CITE_xxx]` tokens with formatted citations.

    For Vancouver / APA / Harvard: `(Author et al., Year)`.
    For IEEE: `[N]` where `N` comes from the `numbering` map (tag → number).

    Unknown tags (model hallucinated) are LEFT UNTOUCHED so reviewers see
    the broken reference rather than silently swallow it.
    """
    def sub(m: re.Match[str]) -> str:
        tag = m.group(1)
        article = articles_by_tag.get(tag)
        if article is None:
            return m.group(0)
        if style == "ieee":
            n = (numbering or {}).get(tag)
            if n is None:
                return m.group(0)
            return ieee_inline(n)
        return f"({format_inline(style, article)})"

    return _CITE_RE.sub(sub, text)


# --- Bibliography entries -----------------------------------------------------

def _normalise_pages(pages: str | None) -> str | None:
    """Render `100-110` as `100–110` (en-dash, per APA/Harvard/IEEE)."""
    if not pages:
        return None
    return pages.replace("-", _EN_DASH)


def _author_list_vancouver(authors: list[str]) -> str:
    """Vancouver: 'Last F, Last F, et al.' Authors as 'First Last' input."""
    if not authors:
        return "Anonymous"
    formatted: list[str] = []
    for a in authors[:6]:
        last, given = _split_name(a)
        if not last:
            continue
        ini = _initials(given)
        formatted.append(f"{last} {ini}" if ini else last)
    if len(authors) > 6:
        formatted.append("et al.")
    return ", ".join(formatted)


def _author_list_apa(authors: list[str]) -> str:
    """APA 7: 'Last, F. M., Last, F., & Last, F.'

    ≤20 authors: list all, ampersand before final.
    21+ authors: first 19, ellipsis, last author (no ampersand).
    """
    if not authors:
        return "Anonymous"
    formatted: list[str] = []
    for a in authors:
        last, given = _split_name(a)
        if not last:
            continue
        ini = _initials_dotted(given)
        formatted.append(f"{last}, {ini}" if ini else last)
    if not formatted:
        return "Anonymous"
    if len(formatted) == 1:
        return formatted[0]
    if len(formatted) <= 20:
        return ", ".join(formatted[:-1]) + f", & {formatted[-1]}"
    head = ", ".join(formatted[:19])
    return f"{head}, ... {formatted[-1]}"


def _author_list_harvard(authors: list[str]) -> str:
    """Harvard: 1 → 'Doe, J.', 2 → 'Doe, J. and Smith, J.', 3+ → 'Doe, J. et al.'"""
    if not authors:
        return "Anon."
    formatted: list[str] = []
    for a in authors[:3]:
        last, given = _split_name(a)
        if not last:
            continue
        ini = _initials_dotted(given)
        formatted.append(f"{last}, {ini}" if ini else last)
    if not formatted:
        return "Anon."
    if len(authors) >= 3 and len(formatted) >= 1:
        return f"{formatted[0]} et al."
    if len(formatted) == 1:
        return formatted[0]
    return f"{formatted[0]} and {formatted[1]}"


def _author_list_ieee(authors: list[str]) -> str:
    """IEEE: initials-first; 1: 'F. Last'; 2: 'F. Last and F. Last';
    3: 'F. Last, F. Last, and F. Last'; 4+: 'F. Last et al.'.
    """
    if not authors:
        return "Anonymous"
    formatted: list[str] = []
    for a in authors[:3]:
        last, given = _split_name(a)
        if not last:
            continue
        ini = " ".join(f"{p[0].upper()}." for p in given if p)
        formatted.append(f"{ini} {last}" if ini else last)
    if not formatted:
        return "Anonymous"
    if len(authors) >= 4:
        return f"{formatted[0]} et al."
    if len(formatted) == 1:
        return formatted[0]
    if len(formatted) == 2:
        return f"{formatted[0]} and {formatted[1]}"
    # exactly 3
    return f"{formatted[0]}, {formatted[1]}, and {formatted[2]}"


# --- Per-style bibliography entry functions ----------------------------------

def vancouver_entry(
    article: _ArticleLike, *, number: int | None = None
) -> str:
    """Vancouver reference-list entry. Byte-identical to the pre-Phase-8 output."""
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
    return " ".join(parts)


def apa7_entry(article: _ArticleLike) -> str:
    """APA 7th edition reference-list entry."""
    authors = _author_list_apa(list(article.authors or []))
    title = (article.title or "Untitled").rstrip(".")
    journal = article.journal or ""
    year = str(article.year) if article.year else "n.d."
    volume = getattr(article, "volume", None)
    issue = getattr(article, "issue", None)
    pages = _normalise_pages(getattr(article, "pages", None))
    doi = article.doi

    author_sep = "" if authors.endswith(".") else "."
    out = f"{authors}{author_sep} ({year}). {title}."
    if journal:
        out += f" {journal}"
        # volume(issue), pages
        if volume:
            seg = f", {volume}"
            if issue:
                seg += f"({issue})"
            if pages:
                seg += f", {pages}"
            out += seg
        elif pages:
            out += f", {pages}"
        out += "."
    if doi:
        out += f" https://doi.org/{doi}"
    return out


def harvard_entry(article: _ArticleLike) -> str:
    """Harvard (Cite Them Right 11) reference-list entry."""
    authors = _author_list_harvard(list(article.authors or []))
    title = (article.title or "Untitled").rstrip(".")
    journal = article.journal or ""
    year = str(article.year) if article.year else "n.d."
    volume = getattr(article, "volume", None)
    issue = getattr(article, "issue", None)
    pages = _normalise_pages(getattr(article, "pages", None))
    doi = article.doi

    out = f"{authors} ({year}) '{title}'"
    if journal:
        out += f", {journal}"
        if volume:
            out += f", {volume}"
            if issue:
                out += f"({issue})"
        if pages:
            out += f", pp. {pages}"
    out += "."
    if doi:
        out += f" doi:{doi}"
    return out


def ieee_entry(article: _ArticleLike) -> str:
    """IEEE reference-list entry. Caller prepends `[N] `."""
    authors = _author_list_ieee(list(article.authors or []))
    title = (article.title or "Untitled").rstrip(".")
    journal = article.journal or ""
    volume = getattr(article, "volume", None)
    issue = getattr(article, "issue", None)
    pages = _normalise_pages(getattr(article, "pages", None))
    year = str(article.year) if article.year else None
    doi = article.doi

    out = f'{authors}, "{title},"'
    tail_parts: list[str] = []
    if journal:
        tail_parts.append(journal)
    if volume:
        tail_parts.append(f"vol. {volume}")
        if issue:
            tail_parts.append(f"no. {issue}")
    if pages:
        tail_parts.append(f"pp. {pages}")
    if year:
        tail_parts.append(year)
    if tail_parts:
        out += " " + ", ".join(tail_parts)
    if doi:
        out += f", doi: {doi}"
    return out + "."


_BIB_FORMATTERS: dict[CitationStyle, Callable[[_ArticleLike], str]] = {
    "vancouver": lambda a: vancouver_entry(a),
    "apa": apa7_entry,
    "harvard": harvard_entry,
    "ieee": ieee_entry,
}


def format_entry(article: _ArticleLike, *, style: CitationStyle = "vancouver") -> str:
    """Style-dispatching reference-list entry.

    Returns plain text. For HTML output use `format_entry_html`.
    Vancouver supports a `number` prefix via `bibliography_entry`; this
    function returns the unnumbered form for APA / Harvard / IEEE.
    """
    if style not in _BIB_FORMATTERS:
        raise ValueError(f"Unknown citation style: {style!r}")
    return _BIB_FORMATTERS[style](article)


def format_entry_html(
    article: _ArticleLike, *, style: CitationStyle = "vancouver"
) -> str:
    """HTML-safe wrapper around `format_entry`. All user data is HTML-escaped."""
    if style not in _BIB_FORMATTERS:
        raise ValueError(f"Unknown citation style: {style!r}")
    # Build a shadow article whose string fields are pre-escaped so the
    # interpolations inside the formatter emit safe markup.
    class _Esc:
        title = escape(article.title or "") if article.title else None
        authors = [escape(a) for a in (article.authors or [])]
        year = article.year
        journal = escape(article.journal or "") if article.journal else None
        doi = escape(article.doi or "") if article.doi else None
        volume = escape(getattr(article, "volume", None) or "") if getattr(article, "volume", None) else None
        issue = escape(getattr(article, "issue", None) or "") if getattr(article, "issue", None) else None
        pages = escape(getattr(article, "pages", None) or "") if getattr(article, "pages", None) else None
    inner = _BIB_FORMATTERS[style](_Esc())  # type: ignore[arg-type]
    return f'<span class="bib-entry">{inner}</span>'


def bibliography_entry(
    article: _ArticleLike, *, number: int | None = None, style: CitationStyle = "vancouver"
) -> str:
    """Single reference-list entry with optional 1-based numbering.

    Vancouver retains its `1. ...` numbered form. APA / Harvard return the
    plain entry (numbering for those styles is handled by the bibliography
    service). IEEE returns `[N] ...` when `number` is given.
    """
    if style == "vancouver":
        return vancouver_entry(article, number=number)
    if style == "ieee":
        body = ieee_entry(article)
        return f"[{number}] {body}" if number is not None else body
    if style not in _BIB_FORMATTERS:
        raise ValueError(f"Unknown citation style: {style!r}")
    return _BIB_FORMATTERS[style](article)


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


def replace_cite_tokens_with_markup(
    text: str,
    articles_by_tag: Mapping[str, _ArticleLike],
    *,
    style: CitationStyle = "vancouver",
    numbering: Mapping[str, int] | None = None,
) -> str:
    """Replace `[CITE_xxx]` tokens with `<sup data-citation>` markup.

    Like `replace_cite_tokens`, but the substituted citation is wrapped in
    a `<sup data-citation data-article-id="xxx">…</sup>` element so the
    bibliography service can discover the referenced article via its
    canonical `data-article-id` attribute (mirrors the TipTap Citation
    node's serialised HTML).

    Unknown tags (article id not in `articles_by_tag`) are left UNTOUCHED
    so reviewers see the broken reference rather than silently swallow it.
    For IEEE style, tags without an entry in `numbering` are also left
    untouched.
    """
    def sub(m: re.Match[str]) -> str:
        tag = m.group(1)
        article = articles_by_tag.get(tag)
        if article is None:
            return m.group(0)
        if style == "ieee":
            n = (numbering or {}).get(tag)
            if n is None:
                return m.group(0)
            inner = ieee_inline(n)
        else:
            inner = f"({format_inline(style, article)})"
        return f'<sup data-citation data-article-id="{escape(tag)}">{inner}</sup>'

    return _CITE_RE.sub(sub, text)
