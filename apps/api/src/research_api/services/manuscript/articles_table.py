"""Phase 4.5 — Build an HTML table summarising a set of articles.

The output is a single ``<table>...</table>`` string ready for TipTap's
``editor.commands.insertContent``. The first column is **always** an
author-year cell carrying the existing Citation NodeView markup so that
inserting the table also wires those articles into the bibliography
(via the same numbering pipeline the editor already runs on every doc
update).

Custom columns (``preset=None``) render empty placeholder cells the user
fills in by hand — by design we never invent extraction data.

The service is pure-functional: route-layer code loads ``Article`` rows,
matching ``ExtractionRecord`` rows (if any), and the project's
``inline_citation_mode``, then hands them down. Anything missing on a
particular article (no extraction, no DOI, etc.) renders as an empty
cell rather than blowing up — partial coverage is the common case for
PROSPERO-style narrative tables.
"""
from __future__ import annotations

from html import escape
from typing import Any, Iterable, Mapping, Protocol

from ...schemas.articles_table import ColumnSpec
from ...services.citation_format import InlineCitationMode


class _ArticleLike(Protocol):
    id: str
    title: str | None
    authors: list[str]
    journal: str | None
    year: int | None
    doi: str | None
    url: str | None
    study_design: str | None


class _ExtractionLike(Protocol):
    article_id: str
    fields: dict[str, Any]


# ── Author/year cell ────────────────────────────────────────────────────


def _last_name(full: str) -> str:
    """Best-effort surname extractor.

    Accepts "Smith J", "John Smith", "Smith, John", "Smith". When the input
    is in "Last, First" order we honour the comma; otherwise we take the
    last whitespace-separated token (which loses nothing for the formats
    above — for "John Smith" we want "Smith"; for "Smith J" we want
    "Smith" too).
    """
    name = (full or "").strip()
    if not name:
        return ""
    if "," in name:
        return name.split(",", 1)[0].strip()
    parts = name.split()
    if len(parts) == 1:
        return parts[0]
    # If the last token is a short initials block (e.g. "Smith J", "Smith JA")
    # then the surname is the first token. Otherwise (e.g. "John Smith") the
    # surname is the last token.
    last = parts[-1]
    if len(last) <= 3 and last.replace(".", "").isupper():
        return parts[0]
    return last


def render_author_year(
    article: _ArticleLike,
    *,
    include_et_al: bool = True,
    include_full_authors: bool = False,
) -> str:
    """Render the "Smith et al. (2024)" string.

    * 1 author → ``Smith (Year)``
    * 2 authors → ``Smith and Jones (Year)``
    * 3+ authors → ``Smith et al. (Year)`` unless ``include_et_al`` is False
      (then full comma-separated surname list)
    * When ``include_full_authors`` is True we always render the full list
      regardless of the et-al toggle — the dialog uses this to opt into
      a "full author list" rendering.
    """
    authors = [a for a in (article.authors or []) if a and a.strip()]
    year_str = str(article.year) if article.year else "n.d."

    if not authors:
        return f"Anonymous ({year_str})"

    surnames = [_last_name(a) for a in authors if _last_name(a)]
    if not surnames:
        return f"Anonymous ({year_str})"

    if include_full_authors or (not include_et_al and len(surnames) >= 3):
        body = ", ".join(surnames)
        return f"{body} ({year_str})"

    if len(surnames) == 1:
        return f"{surnames[0]} ({year_str})"
    if len(surnames) == 2:
        return f"{surnames[0]} and {surnames[1]} ({year_str})"
    return f"{surnames[0]} et al. ({year_str})"


def _citation_sup_markup(article_id: str) -> str:
    """Emit the same `<sup data-citation>` markup the TipTap Citation node
    serialises. The editor's NodeView swaps the inner placeholder ``[…]``
    for the actual ``[N]`` once the citation-number map updates. This is
    the load-bearing contract that lets inserting a table count those
    articles in the bibliography automatically.
    """
    return (
        f'<sup data-citation="true" class="citation" '
        f'data-article-id="{escape(article_id, quote=True)}">[…]</sup>'
    )


# ── Per-preset cell rendering ───────────────────────────────────────────


def _extraction_value(
    fields: dict[str, Any], group: str, key: str
) -> str:
    """Read ``fields[group][key]`` with full type coercion + empty-on-miss."""
    if not isinstance(fields, dict):
        return ""
    g = fields.get(group)
    if not isinstance(g, dict):
        return ""
    v = g.get(key)
    if v is None or v == "":
        return ""
    return str(v)


def _first_outcome_name(fields: dict[str, Any]) -> str:
    """``outcomes`` group accepts either ``{outcomes: [{name, ...}]}`` or
    a bare list. Return the first non-empty name or empty string.
    """
    if not isinstance(fields, dict):
        return ""
    group = fields.get("outcomes")
    items: list[Any] = []
    if isinstance(group, list):
        items = group
    elif isinstance(group, dict):
        if isinstance(group.get("outcomes"), list):
            items = group["outcomes"]
        else:
            # Fallback: the dict itself describes a single outcome.
            items = [group]
    for item in items:
        if isinstance(item, dict):
            name = item.get("name")
            if name:
                return str(name)
    return ""


def _render_cell(
    preset: str | None,
    article: _ArticleLike,
    extraction: _ExtractionLike | None,
    *,
    include_et_al: bool,
    include_full_authors: bool,
    inline_citation_mode: InlineCitationMode,
) -> str:
    """Return the inner HTML for a single ``<td>``.

    Always escape user-supplied strings — only the Citation ``<sup>``
    markup is allowed through as raw HTML and that's emitted by us, not
    sourced from user input.
    """
    if preset is None:
        # Custom column — placeholder, user fills in after insertion.
        return ""

    if preset == "author_year_citation":
        # First column: "Smith et al. (2024) <sup>[N]</sup>". The TipTap
        # NodeView swaps ``[…]`` for the resolved number. ``inline_citation_mode``
        # is kept on the signature so future modes (e.g. author-year
        # styles that don't want a marker) can suppress the <sup>; today
        # all three modes still emit it — the NodeView handles display
        # differences.
        _ = inline_citation_mode  # reserved for future mode-specific suppression
        prose = escape(
            render_author_year(
                article,
                include_et_al=include_et_al,
                include_full_authors=include_full_authors,
            )
        )
        return f"{prose} {_citation_sup_markup(article.id)}"

    fields: dict[str, Any] = (
        extraction.fields if extraction is not None and isinstance(extraction.fields, dict) else {}
    )

    if preset == "title":
        return escape(article.title or "")
    if preset == "journal":
        return escape(article.journal or "")
    if preset == "year":
        return escape(str(article.year) if article.year is not None else "")
    if preset == "doi":
        return escape(article.doi or "")
    if preset == "url":
        return escape(article.url or "")
    if preset == "study_design":
        # Prefer the article's canonical study_design, fall back to
        # extraction.basic.design if absent.
        val = article.study_design or _extraction_value(fields, "basic", "design")
        return escape(val)
    if preset == "country":
        return escape(_extraction_value(fields, "basic", "country"))
    if preset == "sample_size_n":
        return escape(_extraction_value(fields, "population", "n_total"))
    if preset == "intervention":
        return escape(_extraction_value(fields, "intervention", "name"))
    if preset == "comparator":
        return escape(_extraction_value(fields, "comparator", "name"))
    if preset == "primary_outcome":
        return escape(_first_outcome_name(fields))
    if preset == "follow_up":
        # Free-text — extraction schema doesn't enforce a particular group.
        # Try ``outcomes.follow_up`` then ``population.follow_up``.
        val = (
            _extraction_value(fields, "outcomes", "follow_up")
            or _extraction_value(fields, "population", "follow_up")
        )
        return escape(val)
    if preset == "effect_estimate":
        val = (
            _extraction_value(fields, "outcomes", "effect_estimate")
            or _extraction_value(fields, "results", "effect_estimate")
        )
        return escape(val)
    if preset == "risk_of_bias_rating":
        val = _extraction_value(fields, "rob", "overall")
        return escape(val)

    return ""


# ── Public entry point ─────────────────────────────────────────────────


def build_articles_table_html(
    articles: Iterable[_ArticleLike],
    extractions: Mapping[str, _ExtractionLike],
    columns: list[ColumnSpec],
    *,
    inline_citation_mode: InlineCitationMode = "bracket_numeric",
    include_et_al: bool = True,
    include_full_authors: bool = False,
) -> str:
    """Render the final ``<table>`` HTML.

    Contract:
    * The first column is **always** the author/year + citation column,
      even if the caller passes columns that don't include it — we
      synthesise it at the front. (The dialog enforces this on the FE
      side too; this is the defence-in-depth backstop.)
    * Empty cells are ``<td></td>`` (not ``<td>—</td>``) so the editor's
      table NodeView treats them as editable placeholders.
    * The wrapper carries ``class="rma-table rma-articles-table"`` which
      lets the editor's TipTap Table node accept it on paste.
    """
    cols = list(columns)
    has_first = bool(cols) and cols[0].preset == "author_year_citation"
    if not has_first:
        cols = [
            ColumnSpec(preset="author_year_citation", label="Author (Year)"),
            *cols,
        ]

    header_cells: list[str] = []
    for c in cols:
        width_cls = f" data-width=\"{c.width_hint}\"" if c.width_hint else ""
        header_cells.append(
            f'<th{width_cls}><p>{escape(c.label)}</p></th>'
        )
    thead = "<thead><tr>" + "".join(header_cells) + "</tr></thead>"

    body_rows: list[str] = []
    for article in articles:
        extraction = extractions.get(article.id) if extractions else None
        cells: list[str] = []
        for c in cols:
            inner = _render_cell(
                c.preset,
                article,
                extraction,
                include_et_al=include_et_al,
                include_full_authors=include_full_authors,
                inline_citation_mode=inline_citation_mode,
            )
            # TipTap's Table cell expects block content inside <td>; wrap in
            # <p> so the editor doesn't normalise it into something else.
            cells.append(f'<td><p>{inner}</p></td>')
        body_rows.append("<tr>" + "".join(cells) + "</tr>")

    tbody = "<tbody>" + "".join(body_rows) + "</tbody>"
    return (
        '<table class="rma-table rma-articles-table">'
        + thead
        + tbody
        + "</table>"
    )
