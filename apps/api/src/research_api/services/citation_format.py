"""Inline-citation formatting + CITE-token replacement.

This module is the **trust boundary** for citations: every formatted citation
that appears in user-facing text is built here from authoritative `articles`
metadata, never from AI model output. AI generations contain placeholder
tokens like `[CITE_a1]` which this module replaces.
"""
from __future__ import annotations

import re
from datetime import date
from html import escape
from typing import Callable, Literal, Mapping, Protocol

# Phase 16 (MP16) — Extended citation style catalogue.
#
# Vancouver-family journal variants share author + title structure with
# vanilla Vancouver but differ in:
#   * journal abbreviation style (NEJM → "N Engl J Med")
#   * "et al." trigger threshold (NEJM: 3 authors. JBJS: 6 authors per ICMJE.
#     Lancet / BJSM / BJJ / JAMA: 6 authors per ICMJE.)
#   * punctuation around year/volume/pages
CitationStyle = Literal[
    "vancouver",
    "apa",
    "harvard",
    "ieee",
    "lancet",
    "nejm",
    "bjj",
    "jbjs_am",
    "bjsm",
    "jama",
]

# Phase 16 (MP16) — Inline rendering mode for the TipTap CitationNodeView.
InlineCitationMode = Literal[
    "bracket_numeric",
    "superscript_numeric",
    "author_year_parens",
]

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
    # IEEE / Lancet / NEJM / BJJ / JBJS-Am / BJSM / JAMA inline citations are
    # numeric — handled via the dedicated numeric path in
    # `replace_cite_tokens`. These entries exist so `format_inline()` still
    # answers (returns Vancouver-ish author-year for fallback rendering).
    "ieee": vancouver_inline,
    "lancet": vancouver_inline,
    "nejm": vancouver_inline,
    "bjj": vancouver_inline,
    "jbjs_am": vancouver_inline,
    "bjsm": vancouver_inline,
    "jama": vancouver_inline,
}

# Which styles are numeric (use IEEE-style `[N]` inline citations)?
_NUMERIC_STYLES: set[str] = {
    "ieee",
    "lancet",
    "nejm",
    "bjj",
    "jbjs_am",
    "bjsm",
    "jama",
}


def is_numeric_style(style: CitationStyle) -> bool:
    """Return True for styles that render inline citations as ``[N]``.

    Vancouver is excluded because the bibliography layer still emits
    Vancouver as a numbered list but the inline form uses author-year for
    legacy back-compat. The new MP16 numeric variants opt in explicitly.
    """
    return style in _NUMERIC_STYLES


def format_inline_citation(
    *,
    number: int,
    mode: InlineCitationMode = "bracket_numeric",
) -> str:
    """Render a single inline citation marker for a given mode.

    * ``bracket_numeric``       → ``[1]``
    * ``superscript_numeric``   → ``<sup>1</sup>``
    * ``author_year_parens``    → ``(1)`` (numeric fallback — the actual
      author-year string is produced by ``format_inline`` for that mode).

    The CitationNodeView on the frontend mirrors this contract.
    """
    if mode == "superscript_numeric":
        return f"<sup>{number}</sup>"
    if mode == "author_year_parens":
        return f"({number})"
    return f"[{number}]"


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
        if style in _NUMERIC_STYLES:
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


# --- MP16: Vancouver-family journal variants ---------------------------------

def _author_list_journal(authors: list[str], *, et_al_after: int) -> str:
    """Vancouver-style author list with a journal-specific et-al threshold.

    NEJM truncates after 3 listed authors; ICMJE / Vancouver / Lancet / JAMA /
    BJSM / BJJ / JBJS truncate after 6. Callers pass the cutoff so the same
    helper works for all variants.
    """
    if not authors:
        return "Anonymous"
    formatted: list[str] = []
    for a in authors[:et_al_after]:
        last, given = _split_name(a)
        if not last:
            continue
        ini = _initials(given)
        formatted.append(f"{last} {ini}" if ini else last)
    if not formatted:
        return "Anonymous"
    if len(authors) > et_al_after:
        formatted.append("et al.")
    return ", ".join(formatted)


def lancet_entry(article: _ArticleLike) -> str:
    """The Lancet — Vancouver variant.

    Shape: ``Authors. Title. Journal Year; Vol: Pages.``
    Note the single space after ``;`` between year and volume — a Lancet
    quirk that distinguishes it from the NEJM / BJJ / JAMA forms.
    """
    authors = _author_list_journal(list(article.authors or []), et_al_after=6)
    title = (article.title or "Untitled").rstrip(".")
    journal = article.journal or ""
    year = str(article.year) if article.year else "n.d."
    volume = getattr(article, "volume", None)
    pages = getattr(article, "pages", None)
    parts = [f"{authors}.", f"{title}."]
    if journal:
        parts.append(f"{journal}")
    tail = year
    if volume:
        tail += f"; {volume}"
        if pages:
            tail += f": {pages}"
    elif pages:
        tail += f": {pages}"
    parts.append(f"{tail}.")
    if article.doi:
        parts.append(f"doi:{article.doi}")
    return " ".join(parts)


def nejm_entry(article: _ArticleLike) -> str:
    """New England Journal of Medicine — ``et al.`` after **3** authors.

    Shape: ``Authors. Title. Journal Year;Vol:Pages.`` (no spaces inside the
    ``Year;Vol:Pages`` cluster).
    """
    authors = _author_list_journal(list(article.authors or []), et_al_after=3)
    title = (article.title or "Untitled").rstrip(".")
    journal = article.journal or ""
    year = str(article.year) if article.year else "n.d."
    volume = getattr(article, "volume", None)
    pages = getattr(article, "pages", None)
    parts = [f"{authors}.", f"{title}."]
    if journal:
        parts.append(f"{journal}")
    tail = year
    if volume:
        tail += f";{volume}"
        if pages:
            tail += f":{pages}"
    elif pages:
        tail += f":{pages}"
    parts.append(f"{tail}.")
    if article.doi:
        parts.append(f"doi:{article.doi}")
    return " ".join(parts)


def _journal_compact_entry(
    article: _ArticleLike,
    *,
    forced_journal: str | None = None,
    period_after_journal: bool = False,
) -> str:
    """Compact Vancouver variant used by BJJ / JBJS-Am / BJSM / JAMA.

    Shape with ``period_after_journal=False`` (BJJ, BJSM):
        ``Authors. Title. Journal Year;Vol(Issue):Pages.``
    Shape with ``period_after_journal=True`` (JBJS-Am, JAMA):
        ``Authors. Title. Journal. Year;Vol(Issue):Pages.``
    """
    authors = _author_list_journal(list(article.authors or []), et_al_after=6)
    title = (article.title or "Untitled").rstrip(".")
    journal = forced_journal or (article.journal or "")
    year = str(article.year) if article.year else "n.d."
    volume = getattr(article, "volume", None)
    issue = getattr(article, "issue", None)
    pages = getattr(article, "pages", None)

    parts = [f"{authors}.", f"{title}."]
    if journal:
        parts.append(f"{journal}{'.' if period_after_journal else ''}")
    tail = year
    if volume:
        tail += f";{volume}"
        if issue:
            tail += f"({issue})"
        if pages:
            tail += f":{pages}"
    elif pages:
        tail += f":{pages}"
    parts.append(f"{tail}.")
    if article.doi:
        parts.append(f"doi:{article.doi}")
    return " ".join(parts)


def bjj_entry(article: _ArticleLike) -> str:
    """Bone & Joint Journal: ``Bone Joint J Year;Vol(Issue):Pages.``"""
    return _journal_compact_entry(
        article, forced_journal="Bone Joint J", period_after_journal=False
    )


def jbjs_am_entry(article: _ArticleLike) -> str:
    """JBJS American: ``J Bone Joint Surg Am. Year;Vol(Issue):Pages.``"""
    return _journal_compact_entry(
        article, forced_journal="J Bone Joint Surg Am", period_after_journal=True
    )


def bjsm_entry(article: _ArticleLike) -> str:
    """BJSM: ``Br J Sports Med Year;Vol:Pages.`` (no period after journal,
    no issue parenthesis even when issue is present — house style)."""
    authors = _author_list_journal(list(article.authors or []), et_al_after=6)
    title = (article.title or "Untitled").rstrip(".")
    year = str(article.year) if article.year else "n.d."
    volume = getattr(article, "volume", None)
    pages = getattr(article, "pages", None)
    parts = [f"{authors}.", f"{title}.", "Br J Sports Med"]
    tail = year
    if volume:
        tail += f";{volume}"
        if pages:
            tail += f":{pages}"
    elif pages:
        tail += f":{pages}"
    parts.append(f"{tail}.")
    if article.doi:
        parts.append(f"doi:{article.doi}")
    return " ".join(parts)


def jama_entry(article: _ArticleLike) -> str:
    """JAMA: ``JAMA. Year;Vol(Issue):Pages.``"""
    return _journal_compact_entry(
        article, forced_journal="JAMA", period_after_journal=True
    )


# --- MP16: Grey-literature renderers -----------------------------------------

def _grey_lit_entry(article: _ArticleLike) -> str | None:
    """Return a non-journal-article entry when ``reference_type`` warrants it.

    Returns ``None`` when the article is a regular journal article (i.e. the
    caller should fall through to the per-style formatter).
    """
    ref_type = getattr(article, "reference_type", "journal_article") or "journal_article"
    if ref_type == "journal_article":
        return None
    authors = list(article.authors or [])
    title = (article.title or "Untitled").rstrip(".")
    year = str(article.year) if article.year else "n.d."
    url = getattr(article, "url", None) or None
    doi = article.doi
    journal = article.journal or ""  # acts as "server" / "publisher" / etc.

    if ref_type == "web_resource":
        # NLM grey-lit pattern: `Author/Org. Title [Internet]. Year [cited
        # <today>]. Available from: URL`.
        org = ", ".join(authors) if authors else (journal or "Anonymous")
        cited = date.today().isoformat()
        out = f"{org}. {title} [Internet]. {year} [cited {cited}]."
        if url:
            out += f" Available from: {url}"
        return out

    if ref_type == "thesis":
        author_str = _author_list_vancouver(authors)
        univ = journal or "Unknown institution"
        return f"{author_str}. {title} [thesis]. {univ}; {year}."

    if ref_type == "preprint":
        author_str = _author_list_vancouver(authors)
        server = journal or "Preprint server"
        out = f"{author_str}. {title} [preprint]. {server} {year}."
        if doi:
            out += f" doi:{doi}"
        elif url:
            out += f" Available from: {url}"
        return out

    if ref_type == "registry_record":
        out = f"{title}. {journal or 'Registry'}; {year}."
        if url:
            out += f" Available from: {url}"
        return out

    if ref_type == "report":
        author_str = _author_list_vancouver(authors) if authors else (journal or "Anonymous")
        out = f"{author_str}. {title} [report]. {year}."
        if url:
            out += f" Available from: {url}"
        return out

    if ref_type == "book":
        author_str = _author_list_vancouver(authors)
        publisher = journal or ""
        out = f"{author_str}. {title}."
        if publisher:
            out += f" {publisher};"
        out += f" {year}."
        return out

    if ref_type == "book_chapter":
        author_str = _author_list_vancouver(authors)
        book_title = journal or "Untitled book"
        out = f"{author_str}. {title}. In: {book_title}. {year}."
        return out

    if ref_type == "conference_abstract":
        author_str = _author_list_vancouver(authors)
        venue = journal or "Conference"
        out = f"{author_str}. {title} [abstract]. {venue}; {year}."
        return out

    if ref_type == "other":
        author_str = _author_list_vancouver(authors) if authors else "Anonymous"
        out = f"{author_str}. {title}. {year}."
        if url:
            out += f" Available from: {url}"
        return out

    return None


_BIB_FORMATTERS: dict[CitationStyle, Callable[[_ArticleLike], str]] = {
    "vancouver": lambda a: vancouver_entry(a),
    "apa": apa7_entry,
    "harvard": harvard_entry,
    "ieee": ieee_entry,
    "lancet": lancet_entry,
    "nejm": nejm_entry,
    "bjj": bjj_entry,
    "jbjs_am": jbjs_am_entry,
    "bjsm": bjsm_entry,
    "jama": jama_entry,
}

# Per-style "et al." trigger threshold — surfaced for tests + the frontend.
ET_AL_THRESHOLDS: dict[CitationStyle, int] = {
    "vancouver": 6,
    "apa": 20,
    "harvard": 3,
    "ieee": 3,
    "lancet": 6,
    "nejm": 3,
    "bjj": 6,
    "jbjs_am": 6,
    "bjsm": 6,
    "jama": 6,
}


def format_entry(article: _ArticleLike, *, style: CitationStyle = "vancouver") -> str:
    """Style-dispatching reference-list entry.

    Returns plain text. For HTML output use `format_entry_html`.
    Vancouver supports a `number` prefix via `bibliography_entry`; this
    function returns the unnumbered form for APA / Harvard / IEEE.

    Synthetic dataset entries (article.type == "dataset") dispatch to
    `_dataset_entry` so the dataset-specific shape is preserved across both
    numbered (Vancouver/IEEE) and author-year (APA/Harvard) call paths.
    """
    if getattr(article, "type", "article") == "dataset":
        return _dataset_entry(article, number=None, style=style)
    # Phase 16 (MP16) — grey-literature shape takes precedence over the
    # per-style journal-article formatter so e.g. a "thesis" reference reads
    # `Smith J. Title [thesis]. Univ; 2024.` regardless of which Vancouver
    # variant the project is configured to use.
    grey = _grey_lit_entry(article)
    if grey is not None:
        return grey
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
    _ref_type = getattr(article, "reference_type", "journal_article") or "journal_article"
    _url = getattr(article, "url", None) or None

    class _Esc:
        title = escape(article.title or "") if article.title else None
        authors = [escape(a) for a in (article.authors or [])]
        year = article.year
        journal = escape(article.journal or "") if article.journal else None
        doi = escape(article.doi or "") if article.doi else None
        volume = escape(getattr(article, "volume", None) or "") if getattr(article, "volume", None) else None
        issue = escape(getattr(article, "issue", None) or "") if getattr(article, "issue", None) else None
        pages = escape(getattr(article, "pages", None) or "") if getattr(article, "pages", None) else None
        reference_type = _ref_type
        url = escape(_url) if _url else None

    grey = _grey_lit_entry(_Esc())  # type: ignore[arg-type]
    if grey is not None:
        return f'<span class="bib-entry">{grey}</span>'
    inner = _BIB_FORMATTERS[style](_Esc())  # type: ignore[arg-type]
    return f'<span class="bib-entry">{inner}</span>'


def _dataset_entry(
    article: _ArticleLike, *, number: int | None, style: CitationStyle
) -> str:
    """Reference-list entry for synthetic dataset citations.

    Bypasses the article-style author parsing (which would split
    "Project investigators" on whitespace) and emits a clean, dataset-shaped
    citation per style. Author/title/year are surfaced verbatim — the
    `journal` slot is hijacked to hold the "[Internal research dataset]"
    qualifier so the bibliography service only has to set one field.

    Output shape per style:
      Vancouver: `1. Project investigators. <filename>. 2026. [Internal research dataset].`
      IEEE:      `[1] Project investigators, "<filename>", 2026. [Internal research dataset].`
      APA:       `Project investigators. (2026). <filename> [Internal research dataset].`
      Harvard:   `Project investigators (2026) '<filename>'. [Internal research dataset].`
    """
    authors_list = list(article.authors or []) or ["Anonymous"]
    # Render verbatim: dataset authors are pre-formatted (e.g. "Project
    # investigators") so splitting them through `_author_list_*` corrupts them.
    authors = ", ".join(a for a in authors_list if a) or "Anonymous"
    title = (article.title or "Dataset").rstrip(".")
    year = str(article.year) if article.year else "n.d."
    qualifier = article.journal or "[Internal research dataset]"

    if style == "vancouver":
        prefix = f"{number}. " if number is not None else ""
        return f"{prefix}{authors}. {title}. {year}. {qualifier}."
    if style == "ieee":
        prefix = f"[{number}] " if number is not None else ""
        return f'{prefix}{authors}, "{title}", {year}. {qualifier}.'
    if style == "apa":
        return f"{authors}. ({year}). {title} {qualifier}."
    if style == "harvard":
        return f"{authors} ({year}) '{title}'. {qualifier}."
    raise ValueError(f"Unknown citation style: {style!r}")


def bibliography_entry(
    article: _ArticleLike, *, number: int | None = None, style: CitationStyle = "vancouver"
) -> str:
    """Single reference-list entry with optional 1-based numbering.

    Vancouver retains its `1. ...` numbered form. APA / Harvard return the
    plain entry (numbering for those styles is handled by the bibliography
    service). IEEE returns `[N] ...` when `number` is given.

    When the article carries `type == "dataset"` (set by the bibliography
    service for synthetic dataset entries) we dispatch to `_dataset_entry`
    instead — those entries do NOT go through author-list parsing because
    "Project investigators" must be rendered verbatim, not split.
    """
    if getattr(article, "type", "article") == "dataset":
        return _dataset_entry(article, number=number, style=style)
    # Phase 16 (MP16) — grey-literature shape takes precedence and is
    # rendered as a numbered Vancouver-family entry when ``number`` is given.
    grey = _grey_lit_entry(article)
    if grey is not None:
        if style == "vancouver" or style in _NUMERIC_STYLES:
            prefix = f"{number}. " if number is not None else ""
            return f"{prefix}{grey}" if style != "ieee" else (
                f"[{number}] {grey}" if number is not None else grey
            )
        return grey
    if style == "vancouver":
        return vancouver_entry(article, number=number)
    if style == "ieee":
        body = ieee_entry(article)
        return f"[{number}] {body}" if number is not None else body
    if style not in _BIB_FORMATTERS:
        raise ValueError(f"Unknown citation style: {style!r}")
    body = _BIB_FORMATTERS[style](article)
    # The Vancouver-family journal variants (Lancet/NEJM/BJJ/JBJS-Am/BJSM/JAMA)
    # render as numbered lists like Vancouver — prepend "N. " when supplied.
    if style in _NUMERIC_STYLES and style != "ieee" and number is not None:
        return f"{number}. {body}"
    return body


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


# --- Inline-cluster consolidation --------------------------------------------

# A single `<sup data-citation ...>...</sup>` token. Match the full element
# non-greedily so we don't accidentally swallow surrounding markup. The inner
# `[N]` or `(Author, YYYY)` text is captured for inspection.
_SUP_TOKEN_RE = re.compile(
    r'<sup\s+data-citation[^>]*>(?P<inner>[^<]*)</sup>',
    re.DOTALL,
)

# An adjacent cluster: two or more `<sup data-citation>` tokens separated only
# by whitespace. The `(?:WS SUP)+` repeat ensures we capture the full run in
# a single match so the replacement re-emits a consolidated cluster.
_CLUSTER_RE = re.compile(
    r'(?P<cluster>'
    r'<sup\s+data-citation[^>]*>[^<]*</sup>'
    r'(?:\s*<sup\s+data-citation[^>]*>[^<]*</sup>)+'
    r')',
    re.DOTALL,
)

# Within a numeric sup, extract the integer. Allows "[3]" or just "3".
_NUMERIC_INNER_RE = re.compile(r'-?\d+')


def _format_numeric_ranges(numbers: list[int]) -> str:
    """Render a sorted, deduped int list as a Vancouver/IEEE cluster body.

    Single number:      "1"
    Two consecutive:    "1,2"      (two-element runs are NOT collapsed)
    Three+ consecutive: "1-3"      (range)
    Non-contiguous:     "1,3,5"
    Mixed:              "1-3,5"
    """
    if not numbers:
        return ""
    runs: list[list[int]] = [[numbers[0]]]
    for n in numbers[1:]:
        if n == runs[-1][-1] + 1:
            runs[-1].append(n)
        else:
            runs.append([n])
    parts: list[str] = []
    for run in runs:
        if len(run) >= 3:
            parts.append(f"{run[0]}-{run[-1]}")
        else:
            parts.extend(str(n) for n in run)
    return ",".join(parts)


def _consolidate_numeric_cluster(tokens: list[tuple[str, str]]) -> str:
    """Tokens: list of (article_id_attr, inner). Render as a single `<sup>`.

    `article_id_attr` is the original `data-article-id` value for the FIRST
    occurrence of each citation. The consolidated sup keeps `data-citation`
    but emits the comma-joined article ids so downstream tooling can still
    discover them.
    """
    # Preserve first-seen order for article-id mapping, but the displayed
    # numbers sort ascending.
    seen_aids: dict[int, str] = {}
    numbers_in_order: list[int] = []
    for aid, inner in tokens:
        match = _NUMERIC_INNER_RE.search(inner)
        if not match:
            continue
        n = int(match.group(0))
        if n in seen_aids:
            continue
        seen_aids[n] = aid
        numbers_in_order.append(n)
    if not numbers_in_order:
        return ""
    numbers_in_order.sort()
    body = _format_numeric_ranges(numbers_in_order)
    # Single number: just re-emit the original sup form.
    if len(numbers_in_order) == 1:
        n = numbers_in_order[0]
        aid = seen_aids[n]
        attr = f' data-article-id="{escape(aid)}"' if aid else ""
        return f'<sup data-citation{attr}>[{n}]</sup>'
    # Multi-number cluster: keep ALL article ids (comma-joined) so the
    # bibliography service can still discover each, but render the
    # body as a range/list.
    aids = ",".join(seen_aids[n] for n in numbers_in_order if seen_aids.get(n))
    attr = f' data-article-id="{escape(aids)}"' if aids else ""
    return f'<sup data-citation{attr}>[{body}]</sup>'


def _consolidate_author_year_cluster(tokens: list[tuple[str, str]]) -> str:
    """APA / Harvard: merge `(Smith, 2024)(Patel, 2022)` into
    `(Smith, 2024; Patel, 2022)`, dedup, preserve adjacency order."""
    seen: set[str] = set()
    parts: list[str] = []
    aid_order: list[str] = []
    for aid, inner in tokens:
        # Strip outer parens if present so we can join with semicolons.
        body = inner.strip()
        if body.startswith("(") and body.endswith(")"):
            body = body[1:-1].strip()
        if not body or body in seen:
            continue
        seen.add(body)
        parts.append(body)
        if aid and aid not in aid_order:
            aid_order.append(aid)
    if not parts:
        return ""
    if len(parts) == 1:
        # No actual merge happened; re-emit single sup with original aid.
        aid = aid_order[0] if aid_order else ""
        attr = f' data-article-id="{escape(aid)}"' if aid else ""
        return f'<sup data-citation{attr}>({parts[0]})</sup>'
    body = "; ".join(parts)
    aids = ",".join(aid_order)
    attr = f' data-article-id="{escape(aids)}"' if aids else ""
    return f'<sup data-citation{attr}>({body})</sup>'


_DATA_ARTICLE_ID_RE = re.compile(r'data-article-id="([^"]*)"')


def _extract_tokens(cluster_html: str) -> list[tuple[str, str]]:
    """Parse an adjacent run into (article_id, inner_text) tuples."""
    out: list[tuple[str, str]] = []
    for m in _SUP_TOKEN_RE.finditer(cluster_html):
        full = m.group(0)
        inner = m.group("inner") or ""
        aid_m = _DATA_ARTICLE_ID_RE.search(full)
        aid = aid_m.group(1) if aid_m else ""
        out.append((aid, inner))
    return out


def consolidate_inline_clusters(html: str, style: CitationStyle) -> str:
    """Collapse adjacent `<sup data-citation>` tokens into a single span.

    Vancouver / IEEE (numeric):
        `[1][2][3]` → `[1-3]`
        `[1][2]`    → `[1,2]`  (two-token runs are NOT ranged)
        `[3][1][2]` → `[1-3]`  (sorted before range detection)

    APA / Harvard (author-year):
        `(Smith, 2024)(Patel, 2022)` → `(Smith, 2024; Patel, 2022)`

    Adjacency: only whitespace between two `<sup>` tokens counts. Any other
    character — including a comma or a closing tag — breaks the cluster.
    """
    is_numeric = style in _NUMERIC_STYLES or style == "vancouver"

    def replace(match: re.Match[str]) -> str:
        cluster_html = match.group("cluster")
        tokens = _extract_tokens(cluster_html)
        if len(tokens) <= 1:
            return cluster_html
        if is_numeric:
            return _consolidate_numeric_cluster(tokens)
        return _consolidate_author_year_cluster(tokens)

    return _CLUSTER_RE.sub(replace, html)


def replace_cite_tokens_with_markup(
    text: str,
    articles_by_tag: Mapping[str, _ArticleLike],
    *,
    style: CitationStyle = "vancouver",
    numbering: Mapping[str, int] | None = None,
    tag_to_article_id: Mapping[str, str] | None = None,
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

    `tag_to_article_id` lets the caller pin the emitted `data-article-id`
    to a real Article PK when the AI's CITE tag is a short surrogate
    (e.g. `a1`, `a2`). Without this map the tag itself is used as the
    attribute value (back-compat behaviour for callers like the
    statistics push, which use the article id directly as the tag).
    """
    def sub(m: re.Match[str]) -> str:
        tag = m.group(1)
        article = articles_by_tag.get(tag)
        if article is None:
            return m.group(0)
        if style in _NUMERIC_STYLES:
            n = (numbering or {}).get(tag)
            if n is None:
                return m.group(0)
            inner = ieee_inline(n)
        else:
            inner = f"({format_inline(style, article)})"
        article_id = (tag_to_article_id or {}).get(tag, tag)
        return f'<sup data-citation data-article-id="{escape(article_id)}">{inner}</sup>'

    return _CITE_RE.sub(sub, text)
