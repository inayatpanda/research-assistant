"""Compilation routes — aggregation + per-card draft + section draft + reorder.

Citation safety contract: the model only sees CITE tokens (a1, a2, ...) — it
never sees author names or years that it could "invent" from. After the model
returns text, this route replaces tokens with formatted citations from the
authoritative `articles` rows. Unknown tags are left in place so reviewers
spot hallucinated references.
"""
from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..container import Container, get_container
from ..repositories.articles import SqliteArticleRepository
from ..repositories.compilation import CompiledCardRow, SqliteCompilationRepository
from ..repositories.highlights import SqliteHighlightRepository
from ..repositories.projects import SqliteProjectRepository
from ..schemas.compilation import (
    CardDraftResponse,
    CompilationView,
    CompiledCard,
    ReorderRequest,
    SectionDraftResponse,
)
from ..schemas.highlight import HighlightColour, HighlightUpdate
from ..services.ai import (
    AIError,
    AIProviderUnavailable,
    AIRateLimited,
    AISourceInsufficient,
    CardContext,
    SectionDraftContext,
)
from ..services.citation_format import (
    extract_used_citations,
    format_inline,
    replace_cite_tokens_with_markup,
    tag_for_index,
)

router = APIRouter(tags=["compilation"])
log = logging.getLogger("research_api.compilation")

# Mapping colour → human section name (kept consistent with highlight.section field)
COLOUR_TO_SECTION = {
    "intro": "Introduction",
    "method": "Methodology",
    "results": "Results",
    "discussion": "Discussion",
}


async def _session(
    container: Container = Depends(get_container),
) -> AsyncIterator[AsyncSession]:
    async with container.session_factory() as s:
        yield s


def _user_id(container: Container = Depends(get_container)) -> str:
    return container.settings.local_user_id


@dataclass
class _ArticleForCitation:
    """Adapter satisfying citation_format._ArticleLike."""

    title: str | None
    authors: list[str]
    year: int | None
    journal: str | None
    doi: str | None


def _article_for_citation(row: CompiledCardRow) -> _ArticleForCitation:
    return _ArticleForCitation(
        title=row.article_title,
        authors=row.article_authors,
        year=row.article_year,
        journal=row.article_journal,
        doi=row.article_doi,
    )


def _to_compiled_card(row: CompiledCardRow, style: str) -> CompiledCard:
    """Add a server-formatted citation to the wire-level card."""
    citation = format_inline(style, _article_for_citation(row))  # type: ignore[arg-type]
    return CompiledCard(
        highlight_id=row.highlight_id,
        article_id=row.article_id,
        citation=citation,
        article_title=row.article_title,
        article_authors=row.article_authors,
        article_year=row.article_year,
        article_journal=row.article_journal,
        article_doi=row.article_doi,
        page_number=row.page_number,
        selected_text=row.selected_text,
        user_note=row.user_note,
        ai_summary=row.ai_summary,
        section=row.section,  # type: ignore[arg-type]
        colour=row.colour,  # type: ignore[arg-type]
        sort_order=row.sort_order,
    )


@router.get(
    "/projects/{project_id}/compilation/{colour}",
    response_model=CompilationView,
)
async def get_compilation_view(
    project_id: str,
    colour: HighlightColour,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> CompilationView:
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    repo = SqliteCompilationRepository(session)
    rows = await repo.list_cards(project_id, colour, user_id)
    cards = [_to_compiled_card(r, project.citation_style) for r in rows]
    return CompilationView(
        project_id=project_id,
        colour=colour,
        section=COLOUR_TO_SECTION[colour],  # type: ignore[arg-type]
        cards=cards,
    )


def _map_ai_error(e: Exception) -> HTTPException:
    """Map AI provider errors → HTTP status without leaking internal detail."""
    log.warning("AI error: %s: %s", type(e).__name__, e)
    if isinstance(e, AIRateLimited):
        return HTTPException(status_code=429, detail="AI rate limited")
    if isinstance(e, AISourceInsufficient):
        return HTTPException(status_code=422, detail="passage too short to draft")
    return HTTPException(status_code=503, detail="AI provider unavailable")


@router.post(
    "/highlights/{highlight_id}/draft",
    response_model=CardDraftResponse,
)
async def card_draft(
    highlight_id: str,
    container: Container = Depends(get_container),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> CardDraftResponse:
    """Generate a one-sentence draft for a single highlight."""
    hl_repo = SqliteHighlightRepository(session)
    highlight = await hl_repo.get(highlight_id, user_id)
    if highlight is None:
        raise HTTPException(status_code=404, detail="Highlight not found")
    # Need the article for citation formatting
    article = await SqliteArticleRepository(session).get(highlight.article_id, user_id)
    if article is None:
        raise HTTPException(status_code=404, detail="Article not found")
    project = await SqliteProjectRepository(session).get(article.project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    tag = tag_for_index(1)
    ctx = CardContext(
        cite_tag=tag,
        section=highlight.section,
        selected_text=highlight.selected_text,
        user_note=highlight.user_note,
    )
    try:
        raw_draft = await container.ai.generate_card_draft(ctx)
    except (AIProviderUnavailable, AIRateLimited, AISourceInsufficient, AIError) as e:
        raise _map_ai_error(e) from None
    except Exception:
        log.exception("Unexpected AI error in card_draft")
        raise HTTPException(status_code=503, detail="AI provider unavailable") from None

    style = project.citation_style
    article_for_cite = _ArticleForCitation(
        title=article.title,
        authors=list(article.authors or []),
        year=article.year,
        journal=article.journal,
        doi=article.doi,
    )
    # E2E-sweep #C1: emit `<sup data-citation data-article-id="…">` markup
    # rather than plain `(Author, Year)` text so the bibliography panel can
    # discover the referenced article when the user pushes this draft into
    # the manuscript. The cite tag (`a1`) is mapped to the real article PK.
    draft = replace_cite_tokens_with_markup(
        raw_draft,
        {tag: article_for_cite},  # type: ignore[dict-item]
        style=style,
        tag_to_article_id={tag: article.id},
    )
    return CardDraftResponse(
        highlight_id=highlight_id,
        draft=draft,
        used_citation=format_inline(style, article_for_cite),  # type: ignore[arg-type]
    )


@router.post(
    "/projects/{project_id}/compilation/{colour}/draft",
    response_model=SectionDraftResponse,
)
async def section_draft(
    project_id: str,
    colour: HighlightColour,
    container: Container = Depends(get_container),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> SectionDraftResponse:
    """Generate a paragraph draft from all cards of a given colour in the project."""
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    comp = SqliteCompilationRepository(session)
    rows = await comp.list_cards(project_id, colour, user_id)
    if not rows:
        raise HTTPException(status_code=422, detail="No cards in this section to draft from")

    # Build a stable tag map: a1, a2, ...
    tag_to_row: dict[str, CompiledCardRow] = {tag_for_index(i + 1): r for i, r in enumerate(rows)}
    tag_to_article = {
        tag: _article_for_citation(r) for tag, r in tag_to_row.items()
    }
    cards_ctx = [
        CardContext(
            cite_tag=tag,
            section=r.section,
            selected_text=r.selected_text,
            user_note=r.user_note,
        )
        for tag, r in tag_to_row.items()
    ]
    ctx = SectionDraftContext(section=COLOUR_TO_SECTION[colour], cards=cards_ctx)
    try:
        raw_draft = await container.ai.generate_section_draft(ctx)
    except (AIProviderUnavailable, AIRateLimited, AISourceInsufficient, AIError) as e:
        raise _map_ai_error(e) from None
    except Exception:
        log.exception("Unexpected AI error in section_draft")
        raise HTTPException(status_code=503, detail="AI provider unavailable") from None

    style = project.citation_style
    # E2E-sweep #C1: emit `<sup data-citation>` markup with real article
    # PKs as `data-article-id` so the bibliography panel + reference
    # integrity panel pick up citations when the user pushes this draft
    # into a manuscript section. The cite tags (`a1`, `a2`…) are
    # surrogates that we re-map back to the underlying article ids here.
    tag_to_article_id = {tag: r.article_id for tag, r in tag_to_row.items()}
    draft = replace_cite_tokens_with_markup(
        raw_draft,
        tag_to_article,  # type: ignore[arg-type]
        style=style,
        tag_to_article_id=tag_to_article_id,
    )
    used = extract_used_citations(raw_draft, tag_to_article, style=style)  # type: ignore[arg-type]
    return SectionDraftResponse(
        project_id=project_id,
        colour=colour,
        section=COLOUR_TO_SECTION[colour],  # type: ignore[arg-type]
        draft=draft,
        used_citations=used,
    )


@router.patch(
    "/projects/{project_id}/compilation/{colour}/order",
    response_model=CompilationView,
    status_code=status.HTTP_200_OK,
)
async def reorder_cards(
    project_id: str,
    colour: HighlightColour,
    body: ReorderRequest,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> CompilationView:
    """Update sort_order for a batch of highlights, then return the new view.

    Security: each highlight ID in the request body must already be visible in
    this (project, colour) view. Otherwise a caller could pass IDs of highlights
    they own in OTHER projects/colours and silently mutate their sort_order.
    """
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    comp = SqliteCompilationRepository(session)
    rows = await comp.list_cards(project_id, colour, user_id)
    valid_ids = {r.highlight_id for r in rows}

    hl_repo = SqliteHighlightRepository(session)
    for item in body.items:
        if item.highlight_id not in valid_ids:
            # Silently skip out-of-scope IDs rather than 400 — leaking which IDs
            # are valid is itself a small probing signal.
            continue
        await hl_repo.update(
            item.highlight_id, HighlightUpdate(sort_order=item.sort_order), user_id
        )

    rows = await comp.list_cards(project_id, colour, user_id)
    cards = [_to_compiled_card(r, project.citation_style) for r in rows]
    return CompilationView(
        project_id=project_id,
        colour=colour,
        section=COLOUR_TO_SECTION[colour],  # type: ignore[arg-type]
        cards=cards,
    )
