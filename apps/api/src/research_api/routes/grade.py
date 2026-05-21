"""Phase 14 (MP14) — GRADE certainty + Summary-of-Findings routes.

Endpoints:

  GET    /projects/{pid}/review/grade            list assessments
  POST   /projects/{pid}/review/grade            upsert (keyed by outcome_label)
  DELETE /projects/{pid}/review/grade/{grade_id}
  POST   /projects/{pid}/review/grade/push       SoF HTML → Results section
"""
from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..container import Container, get_container
from ..auth_deps import get_current_user
from ..schemas.auth import UserRead
from ..repositories.grade import SqliteGradeRepository
from ..repositories.meta import SqliteMetaRepository
from ..repositories.projects import SqliteProjectRepository
from ..repositories.reviews import SqliteReviewRepository
from ..schemas.grade import (
    GradeAssessmentCreate,
    GradeAssessmentRead,
    GradeAssessmentUpdate,
)
from ..schemas.manuscript_section import ManuscriptSectionRead
from ..services.review.grade import compute_certainty
from ..services.review.sof_table import SofMetaSummary, build_sof_html
from .reviews import _BLOCK_TAG_BY_CLASS, _push_to_section

# Register the SoF table block so subsequent pushes overwrite-by-class.
_BLOCK_TAG_BY_CLASS.setdefault("sof-table", "table")


router = APIRouter(tags=["grade"])


async def _session(
    container: Container = Depends(get_container),
) -> AsyncIterator[AsyncSession]:
    async with container.session_factory() as s:
        yield s


def _user_id(user: UserRead = Depends(get_current_user)) -> str:
    # Phase S1 — delegate to the real session-derived user. The legacy
    # static-id flow remains available via ``RMA_DISABLE_AUTH=1``.
    return user.id


async def _resolve_review(
    project_id: str, session: AsyncSession, user_id: str
):
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    repo = SqliteReviewRepository(session)
    review = await repo.get_or_create(project_id=project_id, user_id=user_id)
    return review


def _derive_certainty_from_create(body: GradeAssessmentCreate) -> str:
    downgrades = {
        "risk_of_bias": body.domain_risk_of_bias,
        "inconsistency": body.domain_inconsistency,
        "indirectness": body.domain_indirectness,
        "imprecision": body.domain_imprecision,
        "publication_bias": body.domain_publication_bias,
    }
    upgrades = {
        "large_effect": body.upgrade_large_effect,
        "dose_response": body.upgrade_dose_response,
        "confounders_against": body.upgrade_confounders_against,
    }
    return compute_certainty(body.starting_certainty, downgrades, upgrades)


@router.get(
    "/projects/{project_id}/review/grade",
    response_model=list[GradeAssessmentRead],
)
async def list_grade(
    project_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> list[GradeAssessmentRead]:
    review = await _resolve_review(project_id, session, user_id)
    repo = SqliteGradeRepository(session)
    rows = await repo.list_for_review(review.id, user_id)
    return [GradeAssessmentRead.model_validate(r) for r in rows]


@router.post(
    "/projects/{project_id}/review/grade",
    response_model=GradeAssessmentRead,
    status_code=status.HTTP_201_CREATED,
)
async def upsert_grade(
    project_id: str,
    body: GradeAssessmentCreate,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> GradeAssessmentRead:
    review = await _resolve_review(project_id, session, user_id)

    # If meta_id is given, validate it lives under this review.
    if body.meta_id:
        meta_repo = SqliteMetaRepository(session)
        meta = await meta_repo.get(body.meta_id, user_id)
        if meta is None or meta.review_id != review.id:
            raise HTTPException(status_code=404, detail="Meta-analysis not found")

    try:
        certainty = _derive_certainty_from_create(body)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None

    repo = SqliteGradeRepository(session)
    row = await repo.upsert(
        project_id=project_id,
        review_id=review.id,
        data=body,
        certainty=certainty,
        user_id=user_id,
    )
    return GradeAssessmentRead.model_validate(row)


@router.delete(
    "/projects/{project_id}/review/grade/{grade_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_grade(
    project_id: str,
    grade_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> None:
    review = await _resolve_review(project_id, session, user_id)
    repo = SqliteGradeRepository(session)
    existing = await repo.get(grade_id, user_id)
    if existing is None or existing.review_id != review.id:
        raise HTTPException(status_code=404, detail="GRADE assessment not found")
    await repo.delete(grade_id, user_id)
    return None


@router.post(
    "/projects/{project_id}/review/grade/push",
    response_model=ManuscriptSectionRead,
)
async def push_grade(
    project_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> ManuscriptSectionRead:
    review = await _resolve_review(project_id, session, user_id)
    repo = SqliteGradeRepository(session)
    rows = await repo.list_for_review(review.id, user_id)

    meta_repo = SqliteMetaRepository(session)
    meta_results: dict[str, SofMetaSummary] = {}
    for row in rows:
        if not row.meta_id or row.meta_id in meta_results:
            continue
        pair = await meta_repo.get_with_inputs(row.meta_id, user_id)
        if pair is None:
            continue
        meta, inputs = pair
        meta_results[row.meta_id] = SofMetaSummary(
            meta_id=meta.id,
            effect_metric=meta.effect_metric,
            n_studies=len(inputs),
            pooled_estimate=meta.pooled_estimate,
            ci_low=meta.ci_low,
            ci_high=meta.ci_high,
            article_ids=tuple(inp.article_id for inp in inputs),
        )

    html = build_sof_html(rows, meta_results)
    return await _push_to_section(
        session,
        project_id=project_id,
        section_name="Results",
        html=html,
        class_hook="sof-table",
        user_id=user_id,
    )
