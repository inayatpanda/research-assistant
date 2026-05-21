"""Phase 17 (MP17) — Stats depth routes.

Endpoints:

  Populations (per dataset CRUD):
    GET    /projects/{pid}/datasets/{did}/populations
    POST   /projects/{pid}/datasets/{did}/populations
    GET    /projects/{pid}/datasets/{did}/populations/{popid}
    PATCH  /projects/{pid}/datasets/{did}/populations/{popid}
    DELETE /projects/{pid}/datasets/{did}/populations/{popid}
    POST   /projects/{pid}/datasets/{did}/populations/{popid}/preview

  Imputation:
    POST   /projects/{pid}/datasets/{did}/impute
    GET    /projects/{pid}/datasets/{did}/imputation-runs

  CACE + sensitivity:
    POST   /projects/{pid}/analyses/{aid}/cace
    POST   /projects/{pid}/analyses/{aid}/sensitivity

  IRR (broader):
    POST   /projects/{pid}/datasets/{did}/irr

  Post-hoc:
    POST   /projects/{pid}/analyses/{aid}/post-hoc

  Instruments:
    GET    /instruments/catalogue
    PATCH  /projects/{pid}/datasets/{did}/variables/{vid}/instrument-binding
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pandas as pd
from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..container import Container, get_container
from ..auth_deps import get_current_user
from ..schemas.auth import UserRead
from ..db.models import DatasetVariable
from ..repositories.analyses import SqliteAnalysisRepository
from ..repositories.datasets import SqliteDatasetRepository
from ..repositories.imputation import SqliteImputationRunRepository
from ..repositories.populations import SqliteAnalysisPopulationRepository
from ..repositories.projects import SqliteProjectRepository
from ..schemas.imputation import (
    CACERequest,
    CACEResponse,
    ImputationRunRead,
    ImputationRunRequest,
    SensitivityRequest,
    SensitivityResponse,
)
from ..schemas.instruments import (
    InstrumentBindingRead,
    InstrumentBindingRequest,
    InstrumentCatalogueResponse,
)
from ..schemas.populations import (
    PopulationApplyPreview,
    PopulationCreate,
    PopulationRead,
    PopulationUpdate,
)
from ..services.instruments.catalogue import is_known_key, list_instruments
from ..services.stats.cace import run_cace_2sls
from ..services.stats.imputation import impute_simple, pool_with_rubin, run_mice
from ..services.stats.ingest import read_dataset, read_table  # noqa: F401
from ..services.stats.irr import (
    fleiss_kappa,
    krippendorff_alpha,
    weighted_kappa,
)
from ..services.stats.post_hoc import (
    bonferroni_pairwise,
    dunns_test,
    games_howell,
    tukey_hsd,
)
from ..services.stats.sensitivity_missing import (
    best_case,
    tipping_point,
    worst_case,
)
from ..services.stats.transform import apply_transformations
from ..services.storage import StorageRef
from ..repositories.transformations import SqliteTransformationRepository
from sqlalchemy import select

router = APIRouter(tags=["stats-depth"])


async def _session(
    container: Container = Depends(get_container),
) -> AsyncIterator[AsyncSession]:
    async with container.session_factory() as s:
        yield s


def _user_id(user: UserRead = Depends(get_current_user)) -> str:
    # Phase S1 — delegate to the real session-derived user. The legacy
    # static-id flow remains available via ``RMA_DISABLE_AUTH=1``.
    return user.id


async def _require_project(
    session: AsyncSession, project_id: str, user_id: str
) -> None:
    proj = await SqliteProjectRepository(session).get(project_id, user_id)
    if proj is None:
        raise HTTPException(status_code=404, detail="Project not found")


async def _require_dataset(
    session: AsyncSession, dataset_id: str, project_id: str, user_id: str
) -> Any:
    ds = await SqliteDatasetRepository(session).get(dataset_id, user_id)
    if ds is None or ds.project_id != project_id:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return ds


async def _load_df(container: Container, session: AsyncSession, dataset: Any, user_id: str) -> pd.DataFrame:
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
    return df


# ─── Populations CRUD ───────────────────────────────────────────────────────


@router.get(
    "/projects/{project_id}/datasets/{dataset_id}/populations",
    response_model=list[PopulationRead],
)
async def list_populations(
    project_id: str,
    dataset_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> list[PopulationRead]:
    await _require_project(session, project_id, user_id)
    await _require_dataset(session, dataset_id, project_id, user_id)
    rows = await SqliteAnalysisPopulationRepository(session).list_for_dataset(
        dataset_id, user_id
    )
    return [PopulationRead.model_validate(r) for r in rows]


@router.post(
    "/projects/{project_id}/datasets/{dataset_id}/populations",
    response_model=PopulationRead,
    status_code=201,
)
async def create_population(
    project_id: str,
    dataset_id: str,
    body: PopulationCreate,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> PopulationRead:
    await _require_project(session, project_id, user_id)
    await _require_dataset(session, dataset_id, project_id, user_id)
    row = await SqliteAnalysisPopulationRepository(session).create(
        dataset_id=dataset_id,
        name=body.name,
        definition=body.definition.model_dump(),
        study_assignment_field=body.study_assignment_field,
        treatment_received_field=body.treatment_received_field,
        user_id=user_id,
    )
    return PopulationRead.model_validate(row)


@router.get(
    "/projects/{project_id}/datasets/{dataset_id}/populations/{population_id}",
    response_model=PopulationRead,
)
async def get_population(
    project_id: str,
    dataset_id: str,
    population_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> PopulationRead:
    await _require_project(session, project_id, user_id)
    await _require_dataset(session, dataset_id, project_id, user_id)
    repo = SqliteAnalysisPopulationRepository(session)
    row = await repo.get(population_id, user_id)
    if row is None or row.dataset_id != dataset_id:
        raise HTTPException(status_code=404, detail="Population not found")
    return PopulationRead.model_validate(row)


@router.patch(
    "/projects/{project_id}/datasets/{dataset_id}/populations/{population_id}",
    response_model=PopulationRead,
)
async def update_population(
    project_id: str,
    dataset_id: str,
    population_id: str,
    body: PopulationUpdate,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> PopulationRead:
    await _require_project(session, project_id, user_id)
    await _require_dataset(session, dataset_id, project_id, user_id)
    repo = SqliteAnalysisPopulationRepository(session)
    row = await repo.get(population_id, user_id)
    if row is None or row.dataset_id != dataset_id:
        raise HTTPException(status_code=404, detail="Population not found")
    updated = await repo.update(
        population_id=population_id,
        user_id=user_id,
        name=body.name,
        definition=body.definition.model_dump() if body.definition is not None else None,
        study_assignment_field=body.study_assignment_field,
        treatment_received_field=body.treatment_received_field,
    )
    assert updated is not None
    return PopulationRead.model_validate(updated)


@router.delete(
    "/projects/{project_id}/datasets/{dataset_id}/populations/{population_id}",
    status_code=204,
)
async def delete_population(
    project_id: str,
    dataset_id: str,
    population_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> None:
    await _require_project(session, project_id, user_id)
    await _require_dataset(session, dataset_id, project_id, user_id)
    repo = SqliteAnalysisPopulationRepository(session)
    row = await repo.get(population_id, user_id)
    if row is None or row.dataset_id != dataset_id:
        raise HTTPException(status_code=404, detail="Population not found")
    await repo.delete(population_id, user_id)
    return None


@router.post(
    "/projects/{project_id}/datasets/{dataset_id}/populations/{population_id}/preview",
    response_model=PopulationApplyPreview,
)
async def preview_population(
    project_id: str,
    dataset_id: str,
    population_id: str,
    container: Container = Depends(get_container),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> PopulationApplyPreview:
    await _require_project(session, project_id, user_id)
    dataset = await _require_dataset(session, dataset_id, project_id, user_id)
    repo = SqliteAnalysisPopulationRepository(session)
    pop = await repo.get(population_id, user_id)
    if pop is None or pop.dataset_id != dataset_id:
        raise HTTPException(status_code=404, detail="Population not found")
    try:
        df = await _load_df(container, session, dataset, user_id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Failed to load dataset: {exc}") from None
    n_before = int(df.shape[0])
    filt = (pop.definition or {}).get("filter") if isinstance(pop.definition, dict) else None
    if filt:
        try:
            df = df.query(filt)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=400, detail=f"Invalid filter expression: {exc}"
            ) from None
    head_rows = df.head(5).to_dict(orient="records")
    return PopulationApplyPreview(
        n_before=n_before, n_after=int(df.shape[0]), head_rows=head_rows
    )


# ─── Imputation ─────────────────────────────────────────────────────────────


@router.post(
    "/projects/{project_id}/datasets/{dataset_id}/impute",
    response_model=ImputationRunRead,
)
async def run_imputation(
    project_id: str,
    dataset_id: str,
    body: ImputationRunRequest,
    container: Container = Depends(get_container),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> ImputationRunRead:
    await _require_project(session, project_id, user_id)
    dataset = await _require_dataset(session, dataset_id, project_id, user_id)
    try:
        df = await _load_df(container, session, dataset, user_id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Failed to load dataset: {exc}") from None
    missing = [c for c in body.target_cols if c not in df.columns]
    if missing:
        raise HTTPException(status_code=400, detail=f"Columns not found: {missing}")

    pooled_summary: dict[str, Any]
    try:
        if body.method == "mice":
            imputed = run_mice(
                df,
                target_cols=body.target_cols,
                n_imputations=body.n_imputations,
                seed=body.seed,
            )
            pooled = pool_with_rubin(imputed, target_cols=body.target_cols)
            pooled_summary = {
                "method": "mice",
                "n_imputations": body.n_imputations,
                "per_column": [p.as_dict() for p in pooled],
            }
        else:
            imputed_df = impute_simple(
                df, method=body.method, target_cols=body.target_cols
            )
            per_col: list[dict[str, Any]] = []
            for c in body.target_cols:
                if pd.api.types.is_numeric_dtype(imputed_df[c]):
                    per_col.append(
                        {
                            "column": c,
                            "q_bar": float(imputed_df[c].mean()),
                            "u_bar": float(imputed_df[c].var(ddof=1) / max(1, len(imputed_df))),
                            "between_var": 0.0,
                            "total_var": float(imputed_df[c].var(ddof=1) / max(1, len(imputed_df))),
                            "se": float(
                                (imputed_df[c].var(ddof=1) / max(1, len(imputed_df))) ** 0.5
                            ),
                            "df": float(len(imputed_df) - 1),
                        }
                    )
            pooled_summary = {
                "method": body.method,
                "n_imputations": 1,
                "per_column": per_col,
            }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    repo = SqliteImputationRunRepository(session)
    row = await repo.create(
        dataset_id=dataset_id,
        method=body.method,
        n_imputations=body.n_imputations,
        seed=body.seed,
        target_cols=list(body.target_cols),
        pooled_summary=pooled_summary,
        user_id=user_id,
    )
    return ImputationRunRead.model_validate(row)


@router.get(
    "/projects/{project_id}/datasets/{dataset_id}/imputation-runs",
    response_model=list[ImputationRunRead],
)
async def list_imputation_runs(
    project_id: str,
    dataset_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> list[ImputationRunRead]:
    await _require_project(session, project_id, user_id)
    await _require_dataset(session, dataset_id, project_id, user_id)
    rows = await SqliteImputationRunRepository(session).list_for_dataset(
        dataset_id, user_id
    )
    return [ImputationRunRead.model_validate(r) for r in rows]


# ─── CACE ───────────────────────────────────────────────────────────────────


async def _require_analysis(
    session: AsyncSession, analysis_id: str, project_id: str, user_id: str
) -> Any:
    analysis = await SqliteAnalysisRepository(session).get(analysis_id, user_id)
    if analysis is None or analysis.project_id != project_id:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis


@router.post(
    "/projects/{project_id}/analyses/{analysis_id}/cace",
    response_model=CACEResponse,
)
async def compute_cace(
    project_id: str,
    analysis_id: str,
    body: CACERequest,
    container: Container = Depends(get_container),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> CACEResponse:
    await _require_project(session, project_id, user_id)
    analysis = await _require_analysis(session, analysis_id, project_id, user_id)
    dataset = await _require_dataset(session, analysis.dataset_id, project_id, user_id)
    try:
        df = await _load_df(container, session, dataset, user_id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Failed to load dataset: {exc}") from None
    for col in (body.outcome, body.assigned, body.received):
        if col not in df.columns:
            raise HTTPException(status_code=400, detail=f"Column {col!r} not found")
    df = df.dropna(subset=[body.outcome, body.assigned, body.received])
    try:
        result = run_cace_2sls(
            y=df[body.outcome].to_numpy(dtype=float),
            d=df[body.received].to_numpy(dtype=float),
            z=df[body.assigned].to_numpy(dtype=float),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return CACEResponse(
        cace_estimate=float(result["cace_estimate"]),
        se=float(result["se"]),
        p=float(result["p"]),
        compliance_rate=float(result["compliance_rate"]),
        n=int(result["n"]),
    )


# ─── Sensitivity ────────────────────────────────────────────────────────────


@router.post(
    "/projects/{project_id}/analyses/{analysis_id}/sensitivity",
    response_model=SensitivityResponse,
)
async def compute_sensitivity(
    project_id: str,
    analysis_id: str,
    body: SensitivityRequest,
    container: Container = Depends(get_container),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> SensitivityResponse:
    await _require_project(session, project_id, user_id)
    analysis = await _require_analysis(session, analysis_id, project_id, user_id)
    dataset = await _require_dataset(session, analysis.dataset_id, project_id, user_id)
    try:
        df = await _load_df(container, session, dataset, user_id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Failed to load dataset: {exc}") from None
    if body.outcome not in df.columns or body.group not in df.columns:
        raise HTTPException(status_code=400, detail="outcome/group column not found")
    try:
        if body.type == "worst_case":
            res = worst_case(df, outcome=body.outcome, group=body.group)
        elif body.type == "best_case":
            res = best_case(df, outcome=body.outcome, group=body.group)
        else:
            res = tipping_point(
                df,
                outcome=body.outcome,
                group=body.group,
                candidate_low=body.candidate_low,
                candidate_high=body.candidate_high,
                alpha=body.alpha,
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return SensitivityResponse(**res)


# ─── IRR ────────────────────────────────────────────────────────────────────


class IRRRequest(BaseModel):
    method: str
    # For fleiss_kappa: a matrix (n_subjects x n_categories); 2D list of ints.
    matrix: list[list[float]] | None = None
    # For krippendorff_alpha: 2D list (raters x items); NaN-friendly (use None).
    ratings: list[list[float | None]] | None = None
    level: str = "nominal"
    # For weighted_kappa: paired ratings.
    rater1: list[float] | None = None
    rater2: list[float] | None = None
    weights: str = "linear"
    n_bootstrap: int = 0
    seed: int = 0


@router.post(
    "/projects/{project_id}/datasets/{dataset_id}/irr",
)
async def run_irr(
    project_id: str,
    dataset_id: str,
    body: IRRRequest,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> dict[str, Any]:
    await _require_project(session, project_id, user_id)
    await _require_dataset(session, dataset_id, project_id, user_id)
    try:
        if body.method == "fleiss":
            if body.matrix is None:
                raise HTTPException(status_code=400, detail="fleiss requires matrix")
            return fleiss_kappa(body.matrix)
        if body.method == "krippendorff":
            if body.ratings is None:
                raise HTTPException(status_code=400, detail="krippendorff requires ratings")
            import numpy as np

            rated = np.asarray(
                [[float("nan") if v is None else float(v) for v in row] for row in body.ratings],
                dtype=float,
            )
            return krippendorff_alpha(rated, level=body.level)  # type: ignore[arg-type]
        if body.method == "weighted_kappa":
            if body.rater1 is None or body.rater2 is None:
                raise HTTPException(
                    status_code=400, detail="weighted_kappa requires rater1 and rater2"
                )
            return weighted_kappa(
                body.rater1,
                body.rater2,
                weights=body.weights,  # type: ignore[arg-type]
                n_bootstrap=body.n_bootstrap,
                seed=body.seed,
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    raise HTTPException(status_code=400, detail=f"unknown method {body.method!r}")


# ─── Post-hoc ───────────────────────────────────────────────────────────────


class PostHocRequest(BaseModel):
    method: str  # tukey | bonferroni | dunns | games_howell
    outcome: str
    groups: str


@router.post(
    "/projects/{project_id}/analyses/{analysis_id}/post-hoc",
)
async def post_hoc_route(
    project_id: str,
    analysis_id: str,
    body: PostHocRequest,
    container: Container = Depends(get_container),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> dict[str, Any]:
    await _require_project(session, project_id, user_id)
    analysis = await _require_analysis(session, analysis_id, project_id, user_id)
    dataset = await _require_dataset(session, analysis.dataset_id, project_id, user_id)
    try:
        df = await _load_df(container, session, dataset, user_id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Failed to load dataset: {exc}") from None
    if body.outcome not in df.columns or body.groups not in df.columns:
        raise HTTPException(status_code=400, detail="outcome/groups column not found")
    df = df.dropna(subset=[body.outcome, body.groups])
    levels = sorted(df[body.groups].unique().tolist(), key=str)
    group_data = {
        str(lv): df.loc[df[body.groups] == lv, body.outcome].to_numpy(dtype=float).tolist()
        for lv in levels
    }
    try:
        if body.method == "tukey":
            rows = tukey_hsd(group_data)
        elif body.method == "bonferroni":
            rows = bonferroni_pairwise(group_data)
        elif body.method == "dunns":
            rows = dunns_test(group_data)
        elif body.method == "games_howell":
            rows = games_howell(group_data)
        else:
            raise HTTPException(status_code=400, detail=f"unknown method {body.method!r}")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return {"method": body.method, "n_groups": len(levels), "pairs": [
        {**{k: v for k, v in r.items() if k != "pair"}, "pair": list(r["pair"])}
        for r in rows
    ]}


# ─── Instruments ────────────────────────────────────────────────────────────


@router.get("/instruments/catalogue", response_model=InstrumentCatalogueResponse)
async def get_instrument_catalogue() -> InstrumentCatalogueResponse:
    return InstrumentCatalogueResponse(instruments=list_instruments())


@router.patch(
    "/projects/{project_id}/datasets/{dataset_id}/variables/{variable_id}/instrument-binding",
    response_model=InstrumentBindingRead,
)
async def patch_instrument_binding(
    project_id: str,
    dataset_id: str,
    variable_id: str,
    body: InstrumentBindingRequest,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> InstrumentBindingRead:
    await _require_project(session, project_id, user_id)
    await _require_dataset(session, dataset_id, project_id, user_id)
    stmt = select(DatasetVariable).where(
        DatasetVariable.id == variable_id, DatasetVariable.user_id == user_id
    )
    var = (await session.execute(stmt)).scalar_one_or_none()
    if var is None or var.dataset_id != dataset_id:
        raise HTTPException(status_code=404, detail="Variable not found")
    if body.instrument_key is not None and not is_known_key(body.instrument_key):
        raise HTTPException(
            status_code=400,
            detail=f"unknown instrument_key {body.instrument_key!r}",
        )
    var.instrument_key = body.instrument_key
    await session.commit()
    await session.refresh(var)
    return InstrumentBindingRead(
        variable_id=variable_id, instrument_key=var.instrument_key
    )
