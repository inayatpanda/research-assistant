"""Phase 13.5 (MP13.5) — Analysis plan + plan run routes.

Endpoints:

  POST   /projects/{pid}/analysis-plans
  GET    /projects/{pid}/analysis-plans
  GET    /projects/{pid}/analysis-plans/{plan_id}
  PATCH  /projects/{pid}/analysis-plans/{plan_id}
  DELETE /projects/{pid}/analysis-plans/{plan_id}
  POST   /projects/{pid}/analysis-plans/{plan_id}/run    body: {dataset_id}
  GET    /projects/{pid}/analysis-plans/{plan_id}/runs
  GET    /projects/{pid}/analysis-plan-runs/{run_id}
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime, timezone

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..container import Container, get_container
from ..repositories.analysis_plans import SqliteAnalysisPlanRepository
from ..repositories.datasets import SqliteDatasetRepository
from ..repositories.projects import SqliteProjectRepository
from ..repositories.transformations import SqliteTransformationRepository
from ..schemas.analysis_plan import (
    AnalysisPlanCreate,
    AnalysisPlanLockRequest,
    AnalysisPlanLockResponse,
    AnalysisPlanRead,
    AnalysisPlanRunRead,
    AnalysisPlanRunRequest,
    AnalysisPlanUpdate,
)
from ..services.export.sap import build_sap_document, compute_integrity_hash
from ..services.stats.ingest import read_dataset, read_table  # noqa: F401
from ..services.stats.plan_runner import run_plan
from ..services.stats.transform import apply_transformations
from ..services.storage import StorageRef
from io import BytesIO

router = APIRouter(tags=["analysis-plans"])


async def _session(
    container: Container = Depends(get_container),
) -> AsyncIterator[AsyncSession]:
    async with container.session_factory() as s:
        yield s


def _user_id(container: Container = Depends(get_container)) -> str:
    return container.settings.local_user_id


async def _require_project(session: AsyncSession, project_id: str, user_id: str) -> None:
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")


@router.post(
    "/projects/{project_id}/analysis-plans",
    response_model=AnalysisPlanRead,
    status_code=201,
)
async def create_plan(
    project_id: str,
    body: AnalysisPlanCreate,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> AnalysisPlanRead:
    await _require_project(session, project_id, user_id)
    repo = SqliteAnalysisPlanRepository(session)
    steps_jsonable = [s.model_dump() for s in body.steps]
    row = await repo.create(
        project_id=project_id,
        name=body.name,
        description=body.description,
        steps=steps_jsonable,
        user_id=user_id,
    )
    return AnalysisPlanRead.model_validate(row)


@router.get(
    "/projects/{project_id}/analysis-plans",
    response_model=list[AnalysisPlanRead],
)
async def list_plans(
    project_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> list[AnalysisPlanRead]:
    await _require_project(session, project_id, user_id)
    rows = await SqliteAnalysisPlanRepository(session).list_for_project(
        project_id, user_id
    )
    return [AnalysisPlanRead.model_validate(r) for r in rows]


@router.get(
    "/projects/{project_id}/analysis-plans/{plan_id}",
    response_model=AnalysisPlanRead,
)
async def get_plan(
    project_id: str,
    plan_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> AnalysisPlanRead:
    row = await SqliteAnalysisPlanRepository(session).get(plan_id, user_id)
    if row is None or row.project_id != project_id:
        raise HTTPException(status_code=404, detail="Plan not found")
    return AnalysisPlanRead.model_validate(row)


@router.patch(
    "/projects/{project_id}/analysis-plans/{plan_id}",
    response_model=AnalysisPlanRead,
)
async def update_plan(
    project_id: str,
    plan_id: str,
    body: AnalysisPlanUpdate,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> AnalysisPlanRead:
    repo = SqliteAnalysisPlanRepository(session)
    row = await repo.get(plan_id, user_id)
    if row is None or row.project_id != project_id:
        raise HTTPException(status_code=404, detail="Plan not found")
    # Phase 17 (MP17) — Pre-registration lock. Refuse mutations unless the
    # caller explicitly forces an unlock.
    if row.is_locked and not body.force_unlock:
        raise HTTPException(
            status_code=409,
            detail=(
                "Plan is locked (pre-registered). Pass force_unlock=true to "
                "override; this will clear the integrity hash."
            ),
        )
    steps_jsonable = (
        [s.model_dump() for s in body.steps] if body.steps is not None else None
    )
    updated = await repo.update(
        plan_id=plan_id,
        user_id=user_id,
        name=body.name,
        description=body.description,
        steps=steps_jsonable,
    )
    assert updated is not None
    if body.force_unlock and updated.is_locked:
        updated.is_locked = False
        updated.locked_at = None
        updated.integrity_hash = None
        await session.commit()
        await session.refresh(updated)
    return AnalysisPlanRead.model_validate(updated)


@router.delete(
    "/projects/{project_id}/analysis-plans/{plan_id}",
    status_code=204,
)
async def delete_plan(
    project_id: str,
    plan_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> None:
    repo = SqliteAnalysisPlanRepository(session)
    row = await repo.get(plan_id, user_id)
    if row is None or row.project_id != project_id:
        raise HTTPException(status_code=404, detail="Plan not found")
    await repo.delete(plan_id, user_id)
    return None


@router.post(
    "/projects/{project_id}/analysis-plans/{plan_id}/run",
    response_model=AnalysisPlanRunRead,
)
async def run_plan_route(
    project_id: str,
    plan_id: str,
    body: AnalysisPlanRunRequest,
    container: Container = Depends(get_container),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> AnalysisPlanRunRead:
    repo = SqliteAnalysisPlanRepository(session)
    plan = await repo.get(plan_id, user_id)
    if plan is None or plan.project_id != project_id:
        raise HTTPException(status_code=404, detail="Plan not found")
    ds_repo = SqliteDatasetRepository(session)
    dataset = await ds_repo.get(body.dataset_id, user_id)
    if dataset is None or dataset.project_id != project_id:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Load df + apply transformations baseline (the plan can further transform)
    try:
        ref = StorageRef(
            backend=dataset.file_ref["backend"], key=dataset.file_ref["key"]
        )
        raw = await container.storage.read(ref)
        df = read_dataset(raw, dataset)
        trepo = SqliteTransformationRepository(session)
        ops = await trepo.list_for_dataset(dataset.id, user_id)
        if ops:
            df = apply_transformations(
                df, [{"op_type": t.op_type, "op_args": t.op_args} for t in ops]
            )
    except Exception as exc:  # noqa: BLE001
        # Stamp the run as fully failed; do not abort the request.
        run_row = await repo.create_run(
            plan_id=plan_id,
            dataset_id=dataset.id,
            result_blob={"steps": []},
            status="failed",
            error=f"Failed to load dataset: {exc}",
            user_id=user_id,
        )
        return AnalysisPlanRunRead.model_validate(run_row)

    # DEMO-FIX-C — Pass display labels to chart renderers.
    variables = await ds_repo.list_variables(dataset.id, user_id)
    display_labels = {v.name: (v.display_label or v.name) for v in variables}
    outcome = run_plan(
        steps=list(plan.steps or []),
        df=df,
        display_labels=display_labels,
    )
    run_row = await repo.create_run(
        plan_id=plan_id,
        dataset_id=dataset.id,
        result_blob=outcome.result_blob,
        status=outcome.status,
        error=outcome.error,
        user_id=user_id,
    )
    return AnalysisPlanRunRead.model_validate(run_row)


@router.get(
    "/projects/{project_id}/analysis-plans/{plan_id}/runs",
    response_model=list[AnalysisPlanRunRead],
)
async def list_runs(
    project_id: str,
    plan_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> list[AnalysisPlanRunRead]:
    repo = SqliteAnalysisPlanRepository(session)
    plan = await repo.get(plan_id, user_id)
    if plan is None or plan.project_id != project_id:
        raise HTTPException(status_code=404, detail="Plan not found")
    rows = await repo.list_runs(plan_id, user_id)
    return [AnalysisPlanRunRead.model_validate(r) for r in rows]


@router.get(
    "/projects/{project_id}/analysis-plan-runs/{run_id}",
    response_model=AnalysisPlanRunRead,
)
async def get_run(
    project_id: str,
    run_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> AnalysisPlanRunRead:
    repo = SqliteAnalysisPlanRepository(session)
    run = await repo.get_run(run_id, user_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    plan = await repo.get(run.plan_id, user_id)
    if plan is None or plan.project_id != project_id:
        raise HTTPException(status_code=404, detail="Run not found")
    return AnalysisPlanRunRead.model_validate(run)


# ─── Phase 17 (MP17) — Pre-registration lock + SAP export ──────────────────


@router.post(
    "/projects/{project_id}/analysis-plans/{plan_id}/lock",
    response_model=AnalysisPlanLockResponse,
)
async def lock_plan(
    project_id: str,
    plan_id: str,
    _body: AnalysisPlanLockRequest | None = None,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> AnalysisPlanLockResponse:
    """Phase 17 (MP17) — pre-register a plan.

    Computes a deterministic SHA-256 over the plan's ``steps`` JSON (sorted
    keys + float rounding) and freezes the plan. Calls are idempotent —
    re-locking an already-locked plan recomputes the hash but does NOT
    advance ``locked_at``.
    """
    repo = SqliteAnalysisPlanRepository(session)
    plan = await repo.get(plan_id, user_id)
    if plan is None or plan.project_id != project_id:
        raise HTTPException(status_code=404, detail="Plan not found")
    steps_list = list(plan.steps or [])
    integrity = compute_integrity_hash(steps_list)
    plan.integrity_hash = integrity
    if not plan.is_locked:
        plan.is_locked = True
        plan.locked_at = datetime.now(tz=timezone.utc)
    await session.commit()
    await session.refresh(plan)
    return AnalysisPlanLockResponse(
        plan_id=plan.id,
        integrity_hash=plan.integrity_hash or integrity,
        locked_at=plan.locked_at or datetime.now(tz=timezone.utc),
    )


@router.get(
    "/projects/{project_id}/analysis-plans/{plan_id}/sap",
)
async def export_sap(
    project_id: str,
    plan_id: str,
    fmt: str = Query("docx", pattern="^(docx|pdf)$", alias="format"),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> StreamingResponse:
    """Stream the SAP document (DOCX or PDF) for ``plan``."""
    repo = SqliteAnalysisPlanRepository(session)
    plan = await repo.get(plan_id, user_id)
    if plan is None or plan.project_id != project_id:
        raise HTTPException(status_code=404, detail="Plan not found")
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    payload = build_sap_document(project, plan, fmt=fmt)
    if fmt == "pdf":
        media_type = "application/pdf"
        filename = f"sap-{plan.id}.pdf"
    else:
        media_type = (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        filename = f"sap-{plan.id}.docx"
    headers = {"Content-Disposition": f"attachment; filename=\"{filename}\""}
    return StreamingResponse(BytesIO(payload), media_type=media_type, headers=headers)
