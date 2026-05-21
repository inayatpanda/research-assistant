"""Highlight CRUD + AI summarise endpoint."""
from __future__ import annotations

import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..container import Container, get_container
from ..auth_deps import get_current_user
from ..schemas.auth import UserRead
from ..repositories.articles import SqliteArticleRepository
from ..repositories.highlights import SqliteHighlightRepository
from ..schemas.highlight import (
    HighlightColour,
    HighlightCreate,
    HighlightRead,
    HighlightUpdate,
)
from ..services.ai import (
    AIError,
    AIProviderUnavailable,
    AIRateLimited,
    AISourceInsufficient,
)

router = APIRouter(tags=["highlights"])
log = logging.getLogger("research_api.highlights")


async def _session(
    container: Container = Depends(get_container),
) -> AsyncIterator[AsyncSession]:
    async with container.session_factory() as s:
        yield s


def _user_id(user: UserRead = Depends(get_current_user)) -> str:
    # Phase S1 — delegate to the real session-derived user. The legacy
    # static-id flow remains available via ``RMA_DISABLE_AUTH=1``.
    return user.id


@router.post(
    "/articles/{article_id}/highlights",
    response_model=HighlightRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_highlight(
    article_id: str,
    data: HighlightCreate,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> HighlightRead:
    # Verify article belongs to user
    article = await SqliteArticleRepository(session).get(article_id, user_id)
    if article is None:
        raise HTTPException(status_code=404, detail="Article not found")
    repo = SqliteHighlightRepository(session)
    h = await repo.create(article_id=article_id, data=data, user_id=user_id)
    return HighlightRead.model_validate(h)


@router.get("/articles/{article_id}/highlights", response_model=list[HighlightRead])
async def list_highlights(
    article_id: str,
    colour: HighlightColour | None = Query(default=None),
    page: int | None = Query(default=None, ge=1),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> list[HighlightRead]:
    repo = SqliteHighlightRepository(session)
    rows = await repo.list_for_article(article_id, user_id, colour=colour, page=page)
    return [HighlightRead.model_validate(h) for h in rows]


@router.patch("/highlights/{highlight_id}", response_model=HighlightRead)
async def update_highlight(
    highlight_id: str,
    patch: HighlightUpdate,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> HighlightRead:
    repo = SqliteHighlightRepository(session)
    h = await repo.update(highlight_id, patch, user_id)
    if h is None:
        raise HTTPException(status_code=404, detail="Highlight not found")
    return HighlightRead.model_validate(h)


@router.delete(
    "/highlights/{highlight_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_highlight(
    highlight_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> None:
    repo = SqliteHighlightRepository(session)
    await repo.delete(highlight_id, user_id)
    return None


@router.post("/highlights/{highlight_id}/summarise", response_model=HighlightRead)
async def summarise_highlight(
    highlight_id: str,
    container: Container = Depends(get_container),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> HighlightRead:
    repo = SqliteHighlightRepository(session)
    h = await repo.get(highlight_id, user_id)
    if h is None:
        raise HTTPException(status_code=404, detail="Highlight not found")
    try:
        summary = await container.ai.summarise(h.selected_text, max_sentences=2)
    except (AIProviderUnavailable, AIRateLimited, AISourceInsufficient, AIError) as e:
        log.warning("AI summarise failed for %s: %s", highlight_id, e)
        # Map provider errors to client-friendly HTTP status without leaking detail.
        if isinstance(e, AIRateLimited):
            raise HTTPException(status_code=429, detail="AI rate limited") from None
        if isinstance(e, AISourceInsufficient):
            raise HTTPException(
                status_code=422, detail="passage too short to summarise"
            ) from None
        raise HTTPException(status_code=503, detail="AI provider unavailable") from None
    except Exception:
        log.exception("Unexpected AI summarise error")
        raise HTTPException(status_code=503, detail="AI provider unavailable") from None
    updated = await repo.update(
        highlight_id, HighlightUpdate(ai_summary=summary), user_id
    )
    assert updated is not None  # we just confirmed ownership
    return HighlightRead.model_validate(updated)
