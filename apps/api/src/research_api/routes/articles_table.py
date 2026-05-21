"""Phase 4.5 — Articles-table render route.

POST /api/projects/{project_id}/manuscript/articles-table

Body: ``BuildArticlesTableRequest`` (article_ids + columns + et-al toggles).
Returns: ``{ html: "<table>...</table>" }`` ready for TipTap insertContent.

Security: the project is loaded under the active user, then every
requested article id is re-validated against the project's article list
*for that same user*. We never read articles by raw id-only — both
``project_id`` and ``user_id`` must match.
"""
from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..container import Container, get_container
from ..repositories.articles import SqliteArticleRepository
from ..repositories.projects import SqliteProjectRepository
from ..repositories.reviews import SqliteReviewRepository
from ..schemas.article import ArticleFilters
from ..schemas.articles_table import (
    BuildArticlesTableRequest,
    BuildArticlesTableResponse,
)
from ..services.manuscript.articles_table import build_articles_table_html


router = APIRouter(tags=["articles_table"])


async def _session(
    container: Container = Depends(get_container),
) -> AsyncIterator[AsyncSession]:
    async with container.session_factory() as s:
        yield s


def _user_id(container: Container = Depends(get_container)) -> str:
    return container.settings.local_user_id


@router.post(
    "/projects/{project_id}/manuscript/articles-table",
    response_model=BuildArticlesTableResponse,
)
async def build_articles_table(
    project_id: str,
    body: BuildArticlesTableRequest,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> BuildArticlesTableResponse:
    project_repo = SqliteProjectRepository(session)
    project = await project_repo.get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    # Defence-in-depth: list the project's articles for THIS user, then filter
    # by the requested ids. An article id from a different user/project simply
    # falls out of the intersection — we never leak rows we shouldn't.
    article_repo = SqliteArticleRepository(session)
    project_articles = await article_repo.list_for_project(
        project_id, user_id, ArticleFilters()
    )
    by_id = {a.id: a for a in project_articles}

    selected = [by_id[aid] for aid in body.article_ids if aid in by_id]
    if not selected:
        raise HTTPException(
            status_code=404,
            detail="No matching articles found for this project",
        )

    # Optional extraction lookup keyed by article_id. The review is
    # auto-created if it doesn't exist yet (so a project without a review
    # still works — every cell just renders empty).
    review_repo = SqliteReviewRepository(session)
    review = await review_repo.get_by_project(project_id, user_id)
    extractions_by_aid: dict[str, object] = {}
    if review is not None:
        for ext in await review_repo.list_extraction(review.id, user_id):
            extractions_by_aid[ext.article_id] = ext

    html = build_articles_table_html(
        selected,
        extractions_by_aid,
        body.columns,
        inline_citation_mode=project.inline_citation_mode,  # type: ignore[arg-type]
        include_et_al=body.include_et_al,
        include_full_authors=body.include_full_authors,
    )
    return BuildArticlesTableResponse(html=html)
