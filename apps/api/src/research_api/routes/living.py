"""Phase 15 (MP15) — Living systematic review routes.

Endpoints (all scoped under /projects/{pid}/review/living):

  GET    /                       → current job (404 if absent)
  POST   /                       → upsert job + (re)register in scheduler
  PATCH  /                       → partial update + reschedule
  DELETE /                       → drop the job + unregister
  POST   /run-now                → manual rerun (for E2E + testing)
  GET    /hits?decision=...      → list hits filtered by decision
  PATCH  /hits/{hit_id}          → dismissed | accepted
  POST   /hits/{hit_id}/import-as-article → ingest accepted hit into library
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..container import Container, get_container
from ..db.models import Article, new_id
from ..repositories.living import SqliteLivingReviewRepository
from ..repositories.projects import SqliteProjectRepository
from ..repositories.reviews import SqliteReviewRepository
from ..schemas.article import ArticleRead
from ..schemas.living import (
    LivingReviewHitDecisionPatch,
    LivingReviewHitRead,
    LivingReviewJobPatch,
    LivingReviewJobRead,
    LivingReviewJobUpsert,
    LivingReviewRunResult,
)
from ..services.ingest.pubmed import fetch_pmid_metadata
from ..services.scheduler.runner import (
    register_job,
    run_job,
    unregister_job,
)

router = APIRouter(tags=["living-review"])


async def _session(
    container: Container = Depends(get_container),
) -> AsyncIterator[AsyncSession]:
    async with container.session_factory() as s:
        yield s


def _user_id(container: Container = Depends(get_container)) -> str:
    return container.settings.local_user_id


async def _resolve(project_id: str, session: AsyncSession, user_id: str):
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    review_repo = SqliteReviewRepository(session)
    review = await review_repo.get_or_create(
        project_id=project_id, user_id=user_id
    )
    return project, review


@router.get(
    "/projects/{project_id}/review/living",
    response_model=LivingReviewJobRead,
)
async def get_job(
    project_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> LivingReviewJobRead:
    _project, review = await _resolve(project_id, session, user_id)
    repo = SqliteLivingReviewRepository(session)
    job = await repo.get_for_review(review.id, user_id)
    if job is None:
        raise HTTPException(status_code=404, detail="No living-review job configured")
    return LivingReviewJobRead.model_validate(job)


@router.post(
    "/projects/{project_id}/review/living",
    response_model=LivingReviewJobRead,
)
async def upsert_job(
    project_id: str,
    body: LivingReviewJobUpsert,
    container: Container = Depends(get_container),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> LivingReviewJobRead:
    _project, review = await _resolve(project_id, session, user_id)
    repo = SqliteLivingReviewRepository(session)
    job = await repo.upsert(
        project_id=project_id,
        review_id=review.id,
        pubmed_query=body.pubmed_query,
        schedule=body.schedule,
        enabled=body.enabled,
        user_id=user_id,
    )
    if job.enabled:
        register_job(
            job.id,
            job.schedule,
            container.session_factory,
            ncbi_api_key=container.settings.ncbi_api_key,
            entrez_email=container.settings.entrez_email,
        )
    else:
        unregister_job(job.id)
    return LivingReviewJobRead.model_validate(job)


@router.patch(
    "/projects/{project_id}/review/living",
    response_model=LivingReviewJobRead,
)
async def patch_job(
    project_id: str,
    body: LivingReviewJobPatch,
    container: Container = Depends(get_container),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> LivingReviewJobRead:
    _project, review = await _resolve(project_id, session, user_id)
    repo = SqliteLivingReviewRepository(session)
    job = await repo.get_for_review(review.id, user_id)
    if job is None:
        raise HTTPException(status_code=404, detail="No living-review job configured")
    updated = await repo.update_fields(
        job_id=job.id,
        user_id=user_id,
        pubmed_query=body.pubmed_query,
        schedule=body.schedule,
        enabled=body.enabled,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="No living-review job configured")
    if updated.enabled:
        register_job(
            updated.id,
            updated.schedule,
            container.session_factory,
            ncbi_api_key=container.settings.ncbi_api_key,
            entrez_email=container.settings.entrez_email,
        )
    else:
        unregister_job(updated.id)
    return LivingReviewJobRead.model_validate(updated)


@router.delete(
    "/projects/{project_id}/review/living",
    status_code=204,
)
async def delete_job(
    project_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> None:
    _project, review = await _resolve(project_id, session, user_id)
    repo = SqliteLivingReviewRepository(session)
    job = await repo.get_for_review(review.id, user_id)
    if job is None:
        raise HTTPException(status_code=404, detail="No living-review job configured")
    job_id = job.id
    await repo.delete(job_id, user_id)
    unregister_job(job_id)


@router.post(
    "/projects/{project_id}/review/living/run-now",
    response_model=LivingReviewRunResult,
)
async def run_now(
    project_id: str,
    container: Container = Depends(get_container),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> LivingReviewRunResult:
    _project, review = await _resolve(project_id, session, user_id)
    repo = SqliteLivingReviewRepository(session)
    job = await repo.get_for_review(review.id, user_id)
    if job is None:
        raise HTTPException(status_code=404, detail="No living-review job configured")

    # Run synchronously through the same session_factory so the new hits are
    # visible to the next GET. run_job opens its own AsyncSession so we
    # must NOT pass the route's session.
    result = await run_job(
        job.id,
        container.session_factory,
        ncbi_api_key=container.settings.ncbi_api_key,
        entrez_email=container.settings.entrez_email,
    )
    return LivingReviewRunResult(
        job_id=job.id,
        new_hits=result.get("new_hits", 0),
        total_fetched=result.get("total", 0),
        ran_at=datetime.now(timezone.utc),
    )


@router.get(
    "/projects/{project_id}/review/living/hits",
    response_model=list[LivingReviewHitRead],
)
async def list_hits(
    project_id: str,
    decision: str | None = Query(default=None, pattern="^(new|dismissed|accepted)$"),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> list[LivingReviewHitRead]:
    _project, review = await _resolve(project_id, session, user_id)
    repo = SqliteLivingReviewRepository(session)
    job = await repo.get_for_review(review.id, user_id)
    if job is None:
        return []
    rows = await repo.list_hits(job_id=job.id, user_id=user_id, decision=decision)
    return [LivingReviewHitRead.model_validate(r) for r in rows]


@router.patch(
    "/projects/{project_id}/review/living/hits/{hit_id}",
    response_model=LivingReviewHitRead,
)
async def patch_hit(
    project_id: str,
    hit_id: str,
    body: LivingReviewHitDecisionPatch,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> LivingReviewHitRead:
    _project, review = await _resolve(project_id, session, user_id)
    repo = SqliteLivingReviewRepository(session)
    job = await repo.get_for_review(review.id, user_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Living-review hit not found")
    hit = await repo.get_hit(hit_id, user_id)
    if hit is None or hit.job_id != job.id:
        raise HTTPException(status_code=404, detail="Living-review hit not found")
    updated = await repo.update_hit_decision(hit_id, user_id, body.decision)
    return LivingReviewHitRead.model_validate(updated)


@router.post(
    "/projects/{project_id}/review/living/hits/{hit_id}/import-as-article",
    response_model=ArticleRead,
)
async def import_hit_as_article(
    project_id: str,
    hit_id: str,
    container: Container = Depends(get_container),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> ArticleRead:
    _project, review = await _resolve(project_id, session, user_id)
    repo = SqliteLivingReviewRepository(session)
    job = await repo.get_for_review(review.id, user_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Living-review hit not found")
    hit = await repo.get_hit(hit_id, user_id)
    if hit is None or hit.job_id != job.id:
        raise HTTPException(status_code=404, detail="Living-review hit not found")
    if hit.decision != "accepted":
        raise HTTPException(
            status_code=422,
            detail="Hit must be marked 'accepted' before import",
        )

    metas = await fetch_pmid_metadata(
        [hit.pmid],
        api_key=container.settings.ncbi_api_key,
        email=container.settings.entrez_email,
    )
    if not metas:
        # Build a minimal fallback so the user isn't blocked by transient
        # PubMed outage — they keep the title from the hit row.
        article = Article(
            id=new_id(),
            user_id=user_id,
            project_id=project_id,
            title=hit.title or "Untitled",
            authors=[],
            pmid=hit.pmid,
            source="pubmed",
        )
    else:
        meta = metas[0]
        article = Article(
            id=new_id(),
            user_id=user_id,
            project_id=project_id,
            title=meta.title or hit.title or "Untitled",
            authors=list(meta.authors or []),
            journal=meta.journal,
            year=meta.year,
            volume=meta.volume,
            issue=meta.issue,
            pages=meta.pages,
            doi=meta.doi,
            pmid=meta.pmid or hit.pmid,
            abstract=meta.abstract,
            source="pubmed",
        )
    session.add(article)
    await session.commit()
    await session.refresh(article)
    return ArticleRead.model_validate(article)
