"""Per-article general notes — single row per (article, user), upsert semantics."""
from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..container import Container, get_container
from ..auth_deps import get_current_user
from ..schemas.auth import UserRead
from ..repositories.articles import SqliteArticleRepository
from ..repositories.notes import SqliteArticleNoteRepository
from ..schemas.note import ArticleNoteRead, ArticleNoteUpsert

router = APIRouter(tags=["notes"])


async def _session(
    container: Container = Depends(get_container),
) -> AsyncIterator[AsyncSession]:
    async with container.session_factory() as s:
        yield s


def _user_id(user: UserRead = Depends(get_current_user)) -> str:
    # Phase S1 — delegate to the real session-derived user. The legacy
    # static-id flow remains available via ``RMA_DISABLE_AUTH=1``.
    return user.id


@router.get("/articles/{article_id}/notes", response_model=ArticleNoteRead)
async def get_note(
    article_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> ArticleNoteRead:
    # Verify article ownership
    article = await SqliteArticleRepository(session).get(article_id, user_id)
    if article is None:
        raise HTTPException(status_code=404, detail="Article not found")
    repo = SqliteArticleNoteRepository(session)
    note = await repo.get(article_id, user_id)
    if note is None:
        # Synthesize an empty note shape so the client can render & autosave-on-first-keystroke
        return ArticleNoteRead(
            id=None,
            user_id=user_id,
            article_id=article_id,
            content="",
            updated_at=None,
        )
    return ArticleNoteRead.model_validate(note)


@router.put("/articles/{article_id}/notes", response_model=ArticleNoteRead)
async def upsert_note(
    article_id: str,
    body: ArticleNoteUpsert,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> ArticleNoteRead:
    article = await SqliteArticleRepository(session).get(article_id, user_id)
    if article is None:
        raise HTTPException(status_code=404, detail="Article not found")
    repo = SqliteArticleNoteRepository(session)
    note = await repo.upsert(article_id=article_id, content=body.content, user_id=user_id)
    return ArticleNoteRead.model_validate(note)
