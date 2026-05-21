"""Narrative synthesis + outcome instruments routes (Phase 19 / MP19)."""
from __future__ import annotations

import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..container import Container, get_container
from ..auth_deps import get_current_user
from ..schemas.auth import UserRead
from ..repositories.projects import SqliteProjectRepository
from ..repositories.reviews import SqliteReviewRepository
from ..repositories.sr_depth import (
    SqliteNarrativeSynthesisRepository,
    SqliteOutcomeInstrumentsRepository,
)
from ..schemas.manuscript_section import ManuscriptSectionRead
from ..schemas.sr_depth import (
    NarrativeSynthesisCreate,
    NarrativeSynthesisRead,
    NarrativeSynthesisUpdate,
    OutcomeInstrumentCreate,
    OutcomeInstrumentRead,
    OutcomeInstrumentUpdate,
)
from ..services.review.narrative_synthesis import (
    build_narrative_table_html,
    build_outcome_instruments_table_html,
)
from .reviews import _push_to_section

router = APIRouter(tags=["sr-depth"])
log = logging.getLogger("research_api.sr_depth")


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


# ── Narrative synthesis ────────────────────────────────────────────────


@router.get(
    "/projects/{project_id}/review/narrative-synthesis",
    response_model=list[NarrativeSynthesisRead],
)
async def list_narrative(
    project_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> list[NarrativeSynthesisRead]:
    review = await _resolve_review(project_id, session, user_id)
    repo = SqliteNarrativeSynthesisRepository(session)
    rows = await repo.list_for_review(review.id, user_id)
    return [NarrativeSynthesisRead.model_validate(r) for r in rows]


@router.post(
    "/projects/{project_id}/review/narrative-synthesis",
    response_model=NarrativeSynthesisRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_narrative(
    project_id: str,
    body: NarrativeSynthesisCreate,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> NarrativeSynthesisRead:
    review = await _resolve_review(project_id, session, user_id)
    repo = SqliteNarrativeSynthesisRepository(session)
    row = await repo.create(
        review_id=review.id,
        user_id=user_id,
        outcome_label=body.outcome_label,
        instrument=body.instrument,
        range_text=body.range_text,
        direction=body.direction,
        narrative_html=body.narrative_html,
        study_citations=body.study_citations,
    )
    return NarrativeSynthesisRead.model_validate(row)


@router.patch(
    "/projects/{project_id}/review/narrative-synthesis/{entry_id}",
    response_model=NarrativeSynthesisRead,
)
async def update_narrative(
    project_id: str,
    entry_id: str,
    body: NarrativeSynthesisUpdate,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> NarrativeSynthesisRead:
    review = await _resolve_review(project_id, session, user_id)
    repo = SqliteNarrativeSynthesisRepository(session)
    existing = await repo.get(entry_id, user_id)
    if existing is None or existing.review_id != review.id:
        raise HTTPException(status_code=404, detail="Narrative entry not found")
    patch = body.model_dump(exclude_unset=True)
    updated = await repo.update(entry_id, patch, user_id)
    if updated is None:
        raise HTTPException(status_code=404, detail="Narrative entry not found")
    return NarrativeSynthesisRead.model_validate(updated)


@router.delete(
    "/projects/{project_id}/review/narrative-synthesis/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_narrative(
    project_id: str,
    entry_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> None:
    review = await _resolve_review(project_id, session, user_id)
    repo = SqliteNarrativeSynthesisRepository(session)
    existing = await repo.get(entry_id, user_id)
    if existing is None or existing.review_id != review.id:
        raise HTTPException(status_code=404, detail="Narrative entry not found")
    await repo.delete(entry_id, user_id)
    return None


@router.post(
    "/projects/{project_id}/review/narrative-synthesis/push",
    response_model=ManuscriptSectionRead,
)
async def push_narrative(
    project_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> ManuscriptSectionRead:
    review = await _resolve_review(project_id, session, user_id)
    repo = SqliteNarrativeSynthesisRepository(session)
    rows = await repo.list_for_review(review.id, user_id)
    entries = [
        {
            "outcome_label": r.outcome_label,
            "instrument": r.instrument,
            "range_text": r.range_text,
            "direction": r.direction,
            "narrative_html": r.narrative_html,
            "study_citations": list(r.study_citations or []),
        }
        for r in rows
    ]
    html = build_narrative_table_html(entries)
    return await _push_to_section(
        session,
        project_id=project_id,
        section_name="Results",
        html=html,
        class_hook="narrative-synthesis-table",
        user_id=user_id,
    )


# ── Outcome instruments ────────────────────────────────────────────────


@router.get(
    "/projects/{project_id}/review/outcome-instruments",
    response_model=list[OutcomeInstrumentRead],
)
async def list_outcome_instruments(
    project_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> list[OutcomeInstrumentRead]:
    review = await _resolve_review(project_id, session, user_id)
    repo = SqliteOutcomeInstrumentsRepository(session)
    rows = await repo.list_for_review(review.id, user_id)
    return [OutcomeInstrumentRead.model_validate(r) for r in rows]


@router.post(
    "/projects/{project_id}/review/outcome-instruments",
    response_model=OutcomeInstrumentRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_outcome_instrument(
    project_id: str,
    body: OutcomeInstrumentCreate,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> OutcomeInstrumentRead:
    review = await _resolve_review(project_id, session, user_id)
    repo = SqliteOutcomeInstrumentsRepository(session)
    row = await repo.create(
        review_id=review.id,
        user_id=user_id,
        outcome_label=body.outcome_label,
        instrument_name=body.instrument_name,
        score_range_low=body.score_range_low,
        score_range_high=body.score_range_high,
        mid=body.mid,
        study_values=[sv.model_dump() for sv in body.study_values],
    )
    return OutcomeInstrumentRead.model_validate(row)


@router.patch(
    "/projects/{project_id}/review/outcome-instruments/{instrument_id}",
    response_model=OutcomeInstrumentRead,
)
async def update_outcome_instrument(
    project_id: str,
    instrument_id: str,
    body: OutcomeInstrumentUpdate,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> OutcomeInstrumentRead:
    review = await _resolve_review(project_id, session, user_id)
    repo = SqliteOutcomeInstrumentsRepository(session)
    existing = await repo.get(instrument_id, user_id)
    if existing is None or existing.review_id != review.id:
        raise HTTPException(status_code=404, detail="Instrument row not found")
    patch = body.model_dump(exclude_unset=True)
    if "study_values" in patch and patch["study_values"] is not None:
        patch["study_values"] = [sv for sv in patch["study_values"]]
    updated = await repo.update(instrument_id, patch, user_id)
    if updated is None:
        raise HTTPException(status_code=404, detail="Instrument row not found")
    return OutcomeInstrumentRead.model_validate(updated)


@router.delete(
    "/projects/{project_id}/review/outcome-instruments/{instrument_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_outcome_instrument(
    project_id: str,
    instrument_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> None:
    review = await _resolve_review(project_id, session, user_id)
    repo = SqliteOutcomeInstrumentsRepository(session)
    existing = await repo.get(instrument_id, user_id)
    if existing is None or existing.review_id != review.id:
        raise HTTPException(status_code=404, detail="Instrument row not found")
    await repo.delete(instrument_id, user_id)
    return None


@router.post(
    "/projects/{project_id}/review/outcome-instruments/push",
    response_model=ManuscriptSectionRead,
)
async def push_outcome_instruments(
    project_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> ManuscriptSectionRead:
    review = await _resolve_review(project_id, session, user_id)
    repo = SqliteOutcomeInstrumentsRepository(session)
    rows = await repo.list_for_review(review.id, user_id)
    payload = [
        {
            "outcome_label": r.outcome_label,
            "instrument_name": r.instrument_name,
            "score_range_low": r.score_range_low,
            "score_range_high": r.score_range_high,
            "mid": r.mid,
            "study_values": list(r.study_values or []),
        }
        for r in rows
    ]
    html = build_outcome_instruments_table_html(payload)
    return await _push_to_section(
        session,
        project_id=project_id,
        section_name="Results",
        html=html,
        class_hook="outcome-instruments-table",
        user_id=user_id,
    )
