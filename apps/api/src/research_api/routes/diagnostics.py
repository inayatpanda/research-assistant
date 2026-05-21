"""DEMO-FIX-A — Standalone diagnostic-test routes.

Lets the user run normality / equal-variance / goodness-of-fit tests
on any column independently of the analysis wizard, and produce visual
diagnostics (Q-Q plot, histogram + normal overlay) on demand.

All endpoints apply the dataset's transformation stack before the test
runs, mirroring ``routes/analyses.py``.
"""
from __future__ import annotations

from collections.abc import AsyncIterator

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from ..container import Container, get_container
from ..auth_deps import get_current_user
from ..schemas.auth import UserRead
from ..db.models import Dataset
from ..repositories.datasets import SqliteDatasetRepository
from ..repositories.projects import SqliteProjectRepository
from ..repositories.transformations import SqliteTransformationRepository
from ..schemas.diagnostics_standalone import (
    DiagnosticRequest,
    DiagnosticResult,
    PlotRequest,
)
from ..services.stats import diagnostics_standalone as diag
from ..services.stats.ingest import read_dataset
from ..services.stats.transform import apply_transformations
from ..services.storage import StorageRef

ALPHA = diag.ALPHA

router = APIRouter(tags=["diagnostics"])


async def _session(
    container: Container = Depends(get_container),
) -> AsyncIterator[AsyncSession]:
    async with container.session_factory() as s:
        yield s


def _user_id(user: UserRead = Depends(get_current_user)) -> str:
    # Phase S1 — delegate to the real session-derived user. The legacy
    # static-id flow remains available via ``RMA_DISABLE_AUTH=1``.
    return user.id


async def _require_dataset(
    session: AsyncSession, project_id: str, dataset_id: str, user_id: str
) -> Dataset:
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    ds = await SqliteDatasetRepository(session).get(dataset_id, user_id)
    if ds is None or ds.project_id != project_id:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return ds


async def _load_df(
    container: Container,
    session: AsyncSession,
    dataset: Dataset,
    user_id: str,
) -> pd.DataFrame:
    ref = StorageRef(backend=dataset.file_ref["backend"], key=dataset.file_ref["key"])
    raw = await container.storage.read(ref)
    df = read_dataset(raw, dataset)
    trepo = SqliteTransformationRepository(session)
    rows = await trepo.list_for_dataset(dataset.id, user_id)
    if not rows:
        return df
    ops = [{"op_type": t.op_type, "op_args": t.op_args} for t in rows]
    return apply_transformations(df, ops)


def _numeric_values(df: pd.DataFrame, column: str) -> list[float]:
    if column not in df.columns:
        raise HTTPException(
            status_code=422, detail=f"Column {column!r} is not in the dataset"
        )
    series = pd.to_numeric(df[column], errors="coerce").dropna()
    return series.astype(float).tolist()


def _grouped_values(
    df: pd.DataFrame, column: str, group_column: str
) -> dict[str, list[float]]:
    if column not in df.columns:
        raise HTTPException(
            status_code=422, detail=f"Column {column!r} is not in the dataset"
        )
    if group_column not in df.columns:
        raise HTTPException(
            status_code=422,
            detail=f"Group column {group_column!r} is not in the dataset",
        )
    out: dict[str, list[float]] = {}
    for level, sub in df.groupby(group_column, dropna=True):
        vals = pd.to_numeric(sub[column], errors="coerce").dropna().tolist()
        if len(vals) >= 2:
            out[str(level)] = [float(v) for v in vals]
    return out


def _ok_from_p(p: float | None) -> bool:
    if p is None:
        return True
    return bool(p > ALPHA)


@router.post(
    "/projects/{project_id}/datasets/{dataset_id}/diagnostics/run",
    response_model=DiagnosticResult,
)
async def run_diagnostic(
    project_id: str,
    dataset_id: str,
    body: DiagnosticRequest,
    container: Container = Depends(get_container),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> DiagnosticResult:
    dataset = await _require_dataset(session, project_id, dataset_id, user_id)
    try:
        df = await _load_df(container, session, dataset, user_id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=422, detail=f"Failed to load dataset: {exc}"
        ) from None

    test_key = body.test_key
    if test_key in {"levene", "bartlett"}:
        if not body.group_column:
            raise HTTPException(
                status_code=422,
                detail=f"{test_key} requires 'group_column'",
            )
        groups = _grouped_values(df, body.column_name, body.group_column)
        if len(groups) < 2:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Need at least 2 groups with ≥ 2 non-missing values "
                    "after grouping"
                ),
            )
        try:
            if test_key == "levene":
                out = diag.levene(groups)
            else:
                out = diag.bartlett(groups)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from None
        ok = _ok_from_p(out["p"])
        return DiagnosticResult(
            test_key=test_key,
            statistic=out["statistic"],
            p=out["p"],
            n=out["n"],
            interpretation=out["interpretation"],
            ok=ok,
            k=out.get("k"),
            center=out.get("center"),
        )

    values = _numeric_values(df, body.column_name)
    try:
        if test_key == "shapiro_wilk":
            out = diag.shapiro_wilk(values)
        elif test_key == "anderson_darling":
            out = diag.anderson_darling(values)
            # AD has no p — derive ok from critical value comparison.
            crit_5 = out["critical_values"].get("5%")
            ok = bool(crit_5 is not None and out["statistic"] <= crit_5)
            return DiagnosticResult(
                test_key=test_key,
                statistic=out["statistic"],
                p=None,
                n=out["n"],
                interpretation=out["interpretation"],
                ok=ok,
                critical_values=out["critical_values"],
                significance_levels=out["significance_levels"],
            )
        elif test_key == "kolmogorov_smirnov":
            out = diag.kolmogorov_smirnov(values)
        elif test_key == "dagostino_pearson":
            out = diag.dagostino_pearson(values)
        else:  # pragma: no cover — guarded by Literal
            raise HTTPException(
                status_code=422, detail=f"Unknown test_key: {test_key}"
            )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None

    return DiagnosticResult(
        test_key=test_key,
        statistic=out["statistic"],
        p=out["p"],
        n=out["n"],
        interpretation=out["interpretation"],
        ok=_ok_from_p(out["p"]),
    )


@router.post(
    "/projects/{project_id}/datasets/{dataset_id}/diagnostics/qq-plot",
)
async def qq_plot(
    project_id: str,
    dataset_id: str,
    body: PlotRequest,
    container: Container = Depends(get_container),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> Response:
    dataset = await _require_dataset(session, project_id, dataset_id, user_id)
    try:
        df = await _load_df(container, session, dataset, user_id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=422, detail=f"Failed to load dataset: {exc}"
        ) from None
    values = _numeric_values(df, body.column_name)
    try:
        png = diag.qq_plot_png(values, title=body.title)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return Response(content=png, media_type="image/png")


@router.post(
    "/projects/{project_id}/datasets/{dataset_id}/diagnostics/histogram",
)
async def histogram(
    project_id: str,
    dataset_id: str,
    body: PlotRequest,
    container: Container = Depends(get_container),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> Response:
    dataset = await _require_dataset(session, project_id, dataset_id, user_id)
    try:
        df = await _load_df(container, session, dataset, user_id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=422, detail=f"Failed to load dataset: {exc}"
        ) from None
    values = _numeric_values(df, body.column_name)
    try:
        png = diag.histogram_normal_overlay_png(values, title=body.title)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return Response(content=png, media_type="image/png")
