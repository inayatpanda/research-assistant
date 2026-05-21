"""Search-strategy CRUD + cross-database translation routes (Phase 19 / MP19)."""
from __future__ import annotations

import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..container import Container, get_container
from ..auth_deps import get_current_user
from ..schemas.auth import UserRead
from ..repositories.projects import SqliteProjectRepository
from ..repositories.reviews import SqliteReviewRepository
from ..repositories.sr_depth import SqliteSearchStrategyRepository
from ..schemas.search_strategy import (
    SearchStrategyCreate,
    SearchStrategyRead,
    SearchStrategyUpdate,
    TranslateResponse,
    TranslationTarget,
)
from ..services.ingest.search_translator import translate

router = APIRouter(tags=["search-strategies"])
log = logging.getLogger("research_api.search_strategies")


async def _session(
    container: Container = Depends(get_container),
) -> AsyncIterator[AsyncSession]:
    async with container.session_factory() as s:
        yield s


def _user_id(user: UserRead = Depends(get_current_user)) -> str:
    # Phase S1 — delegate to the real session-derived user. The legacy
    # static-id flow remains available via ``RMA_DISABLE_AUTH=1``.
    return user.id


async def _resolve_review(project_id: str, session: AsyncSession, user_id: str):
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    repo = SqliteReviewRepository(session)
    review = await repo.get_or_create(project_id=project_id, user_id=user_id)
    return review


@router.get(
    "/projects/{project_id}/review/search-strategies",
    response_model=list[SearchStrategyRead],
)
async def list_search_strategies(
    project_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> list[SearchStrategyRead]:
    review = await _resolve_review(project_id, session, user_id)
    repo = SqliteSearchStrategyRepository(session)
    rows = await repo.list_for_review(review.id, user_id)
    return [SearchStrategyRead.model_validate(r) for r in rows]


@router.post(
    "/projects/{project_id}/review/search-strategies",
    response_model=SearchStrategyRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_search_strategy(
    project_id: str,
    body: SearchStrategyCreate,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> SearchStrategyRead:
    review = await _resolve_review(project_id, session, user_id)
    repo = SqliteSearchStrategyRepository(session)
    if body.translated_from_id:
        src = await repo.get(body.translated_from_id, user_id)
        if src is None or src.review_id != review.id:
            raise HTTPException(
                status_code=422,
                detail="translated_from_id references an unknown strategy",
            )
    row = await repo.create(
        project_id=project_id,
        review_id=review.id,
        user_id=user_id,
        name=body.name,
        database=body.database,
        query_text=body.query_text,
        mesh_term_ids=body.mesh_term_ids,
        translated_from_id=body.translated_from_id,
        is_locked=body.is_locked,
    )
    return SearchStrategyRead.model_validate(row)


@router.patch(
    "/projects/{project_id}/review/search-strategies/{strategy_id}",
    response_model=SearchStrategyRead,
)
async def update_search_strategy(
    project_id: str,
    strategy_id: str,
    body: SearchStrategyUpdate,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> SearchStrategyRead:
    review = await _resolve_review(project_id, session, user_id)
    repo = SqliteSearchStrategyRepository(session)
    existing = await repo.get(strategy_id, user_id)
    if existing is None or existing.review_id != review.id:
        raise HTTPException(status_code=404, detail="Search strategy not found")
    if existing.is_locked and body.is_locked is None:
        raise HTTPException(
            status_code=409, detail="Strategy is locked; unlock before editing"
        )
    patch = body.model_dump(exclude_unset=True)
    updated = await repo.update(strategy_id, patch, user_id)
    if updated is None:
        raise HTTPException(status_code=404, detail="Search strategy not found")
    return SearchStrategyRead.model_validate(updated)


@router.delete(
    "/projects/{project_id}/review/search-strategies/{strategy_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_search_strategy(
    project_id: str,
    strategy_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> None:
    review = await _resolve_review(project_id, session, user_id)
    repo = SqliteSearchStrategyRepository(session)
    existing = await repo.get(strategy_id, user_id)
    if existing is None or existing.review_id != review.id:
        raise HTTPException(status_code=404, detail="Search strategy not found")
    await repo.delete(strategy_id, user_id)
    return None


@router.post(
    "/projects/{project_id}/review/search-strategies/{strategy_id}/translate",
    response_model=TranslateResponse,
)
async def translate_search_strategy(
    project_id: str,
    strategy_id: str,
    to: TranslationTarget = Query(...),
    persist: bool = Query(default=False),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> TranslateResponse:
    review = await _resolve_review(project_id, session, user_id)
    repo = SqliteSearchStrategyRepository(session)
    existing = await repo.get(strategy_id, user_id)
    if existing is None or existing.review_id != review.id:
        raise HTTPException(status_code=404, detail="Search strategy not found")
    result = translate(existing.query_text, source="pubmed", target=to)
    if persist:
        target_db = {
            "embase": "Embase",
            "cochrane": "Cochrane",
            "wos": "Web of Science",
        }[to]
        await repo.create(
            project_id=project_id,
            review_id=review.id,
            user_id=user_id,
            name=f"{existing.name} → {target_db}",
            database=target_db,
            query_text=result.translated_query,
            mesh_term_ids=list(existing.mesh_term_ids or []),
            translated_from_id=strategy_id,
            is_locked=False,
            warnings=list(result.warnings),
        )
    return TranslateResponse(
        translated_query=result.translated_query,
        warnings=list(result.warnings),
        target=to,
    )
