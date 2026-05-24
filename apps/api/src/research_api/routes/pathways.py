"""F3 — Research Pathways HTTP endpoints.

Five guided clinical-research workflows. Each pathway:
  * accepts column references for a dataset under a project,
  * hydrates the dataset bytes (honouring transformations + sheet),
  * dispatches to the matching orchestrator in ``services.pathways``,
  * returns the structured result blob + manuscript-ready prose.

A separate push-to-manuscript endpoint appends the (optionally user-
edited) prose into the project's Methods/Results sections.
"""
from __future__ import annotations

import logging
from collections.abc import AsyncIterator

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth_deps import get_current_user
from ..container import Container, get_container
from ..repositories.datasets import SqliteDatasetRepository
from ..repositories.manuscript_sections import SqliteManuscriptSectionRepository
from ..repositories.projects import SqliteProjectRepository
from ..repositories.transformations import SqliteTransformationRepository
from ..schemas.auth import UserRead
from ..schemas.manuscript_section import ManuscriptSectionRead
from ..schemas.pathways import (
    AgreementRequest,
    DiagnosticRequest,
    PathwayProse,
    PathwayPushRequest,
    PathwayResponse,
    RiskFactorsRequest,
    SurvivalRequest,
    TwoGroupRequest,
)
from ..services.pathways import (
    agreement as agreement_svc,
    diagnostic as diagnostic_svc,
    prose as prose_svc,
    risk_factors as risk_factors_svc,
    survival as survival_svc,
    two_group as two_group_svc,
)
from ..services.stats.ingest import read_dataset
from ..services.stats.transform import apply_transformations
from ..services.storage import StorageRef

router = APIRouter(tags=["pathways"])
log = logging.getLogger("research_api.pathways")


async def _session(
    container: Container = Depends(get_container),
) -> AsyncIterator[AsyncSession]:
    async with container.session_factory() as s:
        yield s


def _user_id(user: UserRead = Depends(get_current_user)) -> str:
    return user.id


async def _hydrate_df(
    *,
    project_id: str,
    dataset_id: str,
    session: AsyncSession,
    container: Container,
    user_id: str,
) -> tuple[pd.DataFrame, dict[str, str]]:
    """Load the dataset + transformation stack into a DataFrame.

    Returns (df, display_labels) where ``display_labels`` maps the
    canonical column name -> the user's free-text label (falls back to
    the canonical name when no override exists).
    """
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    repo = SqliteDatasetRepository(session)
    dataset = await repo.get(dataset_id, user_id)
    if dataset is None or dataset.project_id != project_id:
        raise HTTPException(status_code=404, detail="Dataset not found")

    ref = StorageRef(
        backend=dataset.file_ref["backend"], key=dataset.file_ref["key"]
    )
    try:
        data = await container.storage.read(ref)
    except Exception as exc:  # noqa: BLE001
        log.warning("dataset bytes unreadable: %s", exc)
        raise HTTPException(status_code=410, detail="Dataset file is missing") from None
    try:
        df = read_dataset(data, dataset)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=f"Could not parse dataset: {exc}") from None

    # Apply the transformation stack (same as the data preview).
    trepo = SqliteTransformationRepository(session)
    ops = await trepo.list_for_dataset(dataset_id, user_id)
    if ops:
        try:
            df = apply_transformations(
                df,
                [{"op_type": t.op_type, "op_args": t.op_args} for t in ops],
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("transformation replay failed: %s", exc)

    # Build display labels.
    labels: dict[str, str] = {}
    for v in await repo.list_variables(dataset_id, user_id):
        lbl = getattr(v, "display_label", None)
        if isinstance(lbl, str) and lbl.strip():
            labels[v.name] = lbl
    return df, labels


def _run_or_422(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    except KeyError as exc:
        raise HTTPException(status_code=422, detail=f"missing column: {exc}") from None
    except Exception as exc:  # noqa: BLE001
        log.exception("pathway execution failed")
        raise HTTPException(status_code=500, detail=f"Pathway failed: {exc}") from None


@router.post(
    "/projects/{project_id}/datasets/{dataset_id}/pathways/two-group",
    response_model=PathwayResponse,
)
async def run_two_group(
    project_id: str,
    dataset_id: str,
    body: TwoGroupRequest,
    container: Container = Depends(get_container),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> PathwayResponse:
    df, labels = await _hydrate_df(
        project_id=project_id,
        dataset_id=dataset_id,
        session=session,
        container=container,
        user_id=user_id,
    )
    result = _run_or_422(
        two_group_svc.run, df, outcome=body.outcome, group=body.group
    )
    prose = prose_svc.prose_two_group(result, display_labels=labels)
    return PathwayResponse(
        pathway="two-group",
        result=result,
        prose=PathwayProse(**prose),
    )


@router.post(
    "/projects/{project_id}/datasets/{dataset_id}/pathways/risk-factors",
    response_model=PathwayResponse,
)
async def run_risk_factors(
    project_id: str,
    dataset_id: str,
    body: RiskFactorsRequest,
    container: Container = Depends(get_container),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> PathwayResponse:
    df, labels = await _hydrate_df(
        project_id=project_id,
        dataset_id=dataset_id,
        session=session,
        container=container,
        user_id=user_id,
    )
    result = _run_or_422(
        risk_factors_svc.run,
        df,
        outcome=body.outcome,
        predictors=list(body.predictors),
        confounders=list(body.confounders or []),
    )
    prose = prose_svc.prose_risk_factors(result, display_labels=labels)
    return PathwayResponse(
        pathway="risk-factors",
        result=result,
        prose=PathwayProse(**prose),
    )


@router.post(
    "/projects/{project_id}/datasets/{dataset_id}/pathways/survival",
    response_model=PathwayResponse,
)
async def run_survival(
    project_id: str,
    dataset_id: str,
    body: SurvivalRequest,
    container: Container = Depends(get_container),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> PathwayResponse:
    df, labels = await _hydrate_df(
        project_id=project_id,
        dataset_id=dataset_id,
        session=session,
        container=container,
        user_id=user_id,
    )
    result = _run_or_422(
        survival_svc.run,
        df,
        time=body.time,
        event=body.event,
        strata=body.strata,
        predictors=list(body.predictors or []),
    )
    prose = prose_svc.prose_survival(result, display_labels=labels)
    return PathwayResponse(
        pathway="survival",
        result=result,
        prose=PathwayProse(**prose),
    )


@router.post(
    "/projects/{project_id}/datasets/{dataset_id}/pathways/diagnostic",
    response_model=PathwayResponse,
)
async def run_diagnostic(
    project_id: str,
    dataset_id: str,
    body: DiagnosticRequest,
    container: Container = Depends(get_container),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> PathwayResponse:
    df, labels = await _hydrate_df(
        project_id=project_id,
        dataset_id=dataset_id,
        session=session,
        container=container,
        user_id=user_id,
    )
    result = _run_or_422(
        diagnostic_svc.run,
        df,
        test=body.test,
        reference=body.reference,
        pre_test_probability=body.pre_test_probability,
    )
    prose = prose_svc.prose_diagnostic(result, display_labels=labels)
    return PathwayResponse(
        pathway="diagnostic",
        result=result,
        prose=PathwayProse(**prose),
    )


@router.post(
    "/projects/{project_id}/datasets/{dataset_id}/pathways/agreement",
    response_model=PathwayResponse,
)
async def run_agreement(
    project_id: str,
    dataset_id: str,
    body: AgreementRequest,
    container: Container = Depends(get_container),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> PathwayResponse:
    df, labels = await _hydrate_df(
        project_id=project_id,
        dataset_id=dataset_id,
        session=session,
        container=container,
        user_id=user_id,
    )
    result = _run_or_422(
        agreement_svc.run,
        df,
        rater_a=body.rater_a,
        rater_b=body.rater_b,
        ordinal=body.ordinal,
    )
    prose = prose_svc.prose_agreement(result, display_labels=labels)
    return PathwayResponse(
        pathway="agreement",
        result=result,
        prose=PathwayProse(**prose),
    )


@router.post(
    "/projects/{project_id}/datasets/{dataset_id}/pathways/push-to-manuscript",
    response_model=dict,
    status_code=status.HTTP_200_OK,
)
async def push_pathway_prose(
    project_id: str,
    dataset_id: str,
    body: PathwayPushRequest,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> dict:
    """Append the pathway's prose into Methods/Results manuscript sections.

    Returns ``{"methods": ManuscriptSectionRead|None, "results":
    ManuscriptSectionRead|None}``. Either field is null when ``target``
    was not requested.
    """
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    repo = SqliteDatasetRepository(session)
    dataset = await repo.get(dataset_id, user_id)
    if dataset is None or dataset.project_id != project_id:
        raise HTTPException(status_code=404, detail="Dataset not found")

    if body.target in {"methods", "both"} and not (body.methods or "").strip():
        raise HTTPException(
            status_code=422, detail="methods prose is empty"
        )
    if body.target in {"results", "both"} and not (body.results or "").strip():
        raise HTTPException(
            status_code=422, detail="results prose is empty"
        )

    sec_repo = SqliteManuscriptSectionRepository(session)
    out: dict[str, ManuscriptSectionRead | None] = {
        "methods": None,
        "results": None,
    }

    async def _append(section_name: str, prose: str) -> ManuscriptSectionRead:
        existing = await sec_repo.get(
            project_id=project_id, section_name=section_name, user_id=user_id
        )
        paragraph = f"<p>{prose}</p>"
        new_content = paragraph if existing is None or not existing.content else (
            existing.content + paragraph
        )
        updated = await sec_repo.upsert(
            project_id=project_id,
            section_name=section_name,
            content=new_content,
            user_id=user_id,
        )
        return ManuscriptSectionRead.model_validate(updated)

    # The manuscript section catalogue uses "Methodology" rather than "Methods".
    if body.target in {"methods", "both"}:
        out["methods"] = await _append("Methodology", body.methods or "")
    if body.target in {"results", "both"}:
        out["results"] = await _append("Results", body.results or "")
    return {
        "methods": out["methods"].model_dump(mode="json") if out["methods"] else None,
        "results": out["results"].model_dump(mode="json") if out["results"] else None,
        "pathway": body.pathway,
        "dataset_id": dataset_id,
    }
