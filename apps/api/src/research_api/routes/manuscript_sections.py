"""ManuscriptSection routes — GET (synthesizes empty) + PUT upsert.

Each manuscript section (Introduction/Methodology/Results/Discussion/Abstract/
Conclusion) is one row per (project, user). Phase 4 stores plain text; Phase 5
will swap to TipTap JSON.
"""
from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..container import Container, get_container
from ..auth_deps import get_current_user
from ..schemas.auth import UserRead
from ..repositories.articles import SqliteArticleRepository
from ..repositories.manuscript_sections import SqliteManuscriptSectionRepository
from ..repositories.projects import SqliteProjectRepository
from ..schemas.manuscript_section import (
    ManuscriptSectionName,
    ManuscriptSectionRead,
    ManuscriptSectionUpsert,
)
from ..services.citation_format import (
    CitationStyle,
    _CITE_RE,
    _INNER_CITE_RE,
    replace_cite_tokens_with_markup,
)

router = APIRouter(tags=["manuscript_sections"])


async def _session(
    container: Container = Depends(get_container),
) -> AsyncIterator[AsyncSession]:
    async with container.session_factory() as s:
        yield s


def _user_id(user: UserRead = Depends(get_current_user)) -> str:
    # Phase S1 — delegate to the real session-derived user. The legacy
    # static-id flow remains available via ``RMA_DISABLE_AUTH=1``.
    return user.id


@router.get(
    "/projects/{project_id}/sections/{section_name}",
    response_model=ManuscriptSectionRead,
)
async def get_section(
    project_id: str,
    section_name: ManuscriptSectionName,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> ManuscriptSectionRead:
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    repo = SqliteManuscriptSectionRepository(session)
    row = await repo.get(
        project_id=project_id, section_name=section_name, user_id=user_id
    )
    if row is None:
        return ManuscriptSectionRead(
            id=None,
            user_id=user_id,
            project_id=project_id,
            section_name=section_name,
            content="",
            word_count=0,
            updated_at=None,
        )
    # Lazy resolve any legacy `[CITE_<article_id>]` tokens that may have been
    # persisted before the resolver was wired into the meta-analysis push
    # path (rcm-sweep HIGH bug). Tokens with unknown ids are left intact so
    # researchers can still see the broken reference.
    content = row.content or ""
    if "[CITE_" in content:
        try:
            content = await _resolve_legacy_cite_tokens(
                content, project_id=project_id, user_id=user_id, session=session
            )
        except Exception:
            # Resolver is best-effort — never block a section read.
            content = row.content or ""
    return ManuscriptSectionRead(
        id=row.id,
        user_id=row.user_id,
        project_id=row.project_id,
        section_name=row.section_name,
        content=content,
        word_count=row.word_count,
        updated_at=row.updated_at,
    )


async def _resolve_legacy_cite_tokens(
    content: str,
    *,
    project_id: str,
    user_id: str,
    session: AsyncSession,
) -> str:
    """Resolve `[CITE_<aid>]` tokens carried in legacy section content.

    Tokens referencing articles that exist in the project's library are
    rewritten to `<sup data-citation data-article-id="...">[N]</sup>`
    markup. Tokens referencing unknown ids are left untouched so the
    user still sees the orphan reference.
    """
    # Collect every token id present. `_INNER_CITE_RE` matches the inner
    # ``CITE_xxx`` form so we also pick up ids inside combined-bracket
    # clusters like ``[CITE_a, CITE_b]`` — `replace_cite_tokens_with_markup`
    # already calls `_normalise_cite_tokens` to split those into well-formed
    # ``[CITE_xxx]`` tokens before substitution.
    token_ids = {m.group(1) for m in _INNER_CITE_RE.finditer(content)}
    if not token_ids:
        return content
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    style: CitationStyle = (
        project.citation_style  # type: ignore[assignment]
        if project is not None
        and project.citation_style in ("vancouver", "apa", "harvard", "ieee")
        else "vancouver"
    )
    art_repo = SqliteArticleRepository(session)
    articles_by_tag: dict[str, object] = {}
    for aid in token_ids:
        art = await art_repo.get(aid, user_id)
        if art is not None:
            articles_by_tag[aid] = art
    if not articles_by_tag:
        return content
    numbering: dict[str, int] | None = None
    if style == "ieee":
        # Number tokens in first-seen order so re-reads stay stable.
        numbering = {}
        n = 1
        for m in _CITE_RE.finditer(content):
            tag = m.group(1)
            if tag in articles_by_tag and tag not in numbering:
                numbering[tag] = n
                n += 1
    return replace_cite_tokens_with_markup(
        content, articles_by_tag, style=style, numbering=numbering
    )


@router.put(
    "/projects/{project_id}/sections/{section_name}",
    response_model=ManuscriptSectionRead,
)
async def upsert_section(
    project_id: str,
    section_name: ManuscriptSectionName,
    body: ManuscriptSectionUpsert,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> ManuscriptSectionRead:
    if body.section_name != section_name:
        raise HTTPException(
            status_code=422,
            detail="section_name in path must match body.section_name",
        )
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    repo = SqliteManuscriptSectionRepository(session)
    row = await repo.upsert(
        project_id=project_id,
        section_name=section_name,
        content=body.content,
        user_id=user_id,
    )
    return ManuscriptSectionRead.model_validate(row)
