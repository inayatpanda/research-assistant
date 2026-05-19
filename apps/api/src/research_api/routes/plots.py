"""Phase 13.5 (MP13.5) — Dataset plot routes.

Endpoints:

  POST   /projects/{pid}/datasets/{did}/plots             create + render
  GET    /projects/{pid}/datasets/{did}/plots             list
  GET    /projects/{pid}/plots/{plot_id}                  single
  DELETE /projects/{pid}/plots/{plot_id}                  delete
  POST   /projects/{pid}/plots/{plot_id}/regenerate       re-render
"""
from __future__ import annotations

import base64
from collections.abc import AsyncIterator

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..container import Container, get_container
from ..db.models import Dataset
from ..repositories.datasets import SqliteDatasetRepository
from ..repositories.plots import SqlitePlotRepository
from ..repositories.projects import SqliteProjectRepository
from ..repositories.transformations import SqliteTransformationRepository
from ..schemas.plot import PlotCreate, PlotRead
from ..services.stats.ingest import read_dataset, read_table  # noqa: F401
from ..services.stats.plot_renderer import PlotRenderError, render_plot
from ..services.stats.transform import apply_transformations
from ..services.storage import StorageRef

router = APIRouter(tags=["plots"])


async def _session(
    container: Container = Depends(get_container),
) -> AsyncIterator[AsyncSession]:
    async with container.session_factory() as s:
        yield s


def _user_id(container: Container = Depends(get_container)) -> str:
    return container.settings.local_user_id


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


def _render_to_uri(df: pd.DataFrame, spec: dict) -> str:
    png = render_plot(df, spec)
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")


@router.post(
    "/projects/{project_id}/datasets/{dataset_id}/plots",
    response_model=PlotRead,
    status_code=201,
)
async def create_plot(
    project_id: str,
    dataset_id: str,
    body: PlotCreate,
    container: Container = Depends(get_container),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> PlotRead:
    dataset = await _require_dataset(session, project_id, dataset_id, user_id)
    try:
        df = await _load_df(container, session, dataset, user_id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=f"Failed to load dataset: {exc}") from None
    spec = {
        "geom": body.geom,
        "x": body.x,
        "y": body.y,
        "color": body.color,
        "facet": body.facet,
        "args": body.args,
    }
    try:
        data_uri = _render_to_uri(df, spec)
    except PlotRenderError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    row = await SqlitePlotRepository(session).create(
        project_id=project_id,
        dataset_id=dataset_id,
        title=body.title,
        spec=spec,
        png_data_uri=data_uri,
        user_id=user_id,
    )
    return PlotRead.model_validate(row)


@router.get(
    "/projects/{project_id}/datasets/{dataset_id}/plots",
    response_model=list[PlotRead],
)
async def list_plots(
    project_id: str,
    dataset_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> list[PlotRead]:
    await _require_dataset(session, project_id, dataset_id, user_id)
    rows = await SqlitePlotRepository(session).list_for_dataset(dataset_id, user_id)
    return [PlotRead.model_validate(r) for r in rows]


@router.get(
    "/projects/{project_id}/plots/{plot_id}",
    response_model=PlotRead,
)
async def get_plot(
    project_id: str,
    plot_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> PlotRead:
    row = await SqlitePlotRepository(session).get(plot_id, user_id)
    if row is None or row.project_id != project_id:
        raise HTTPException(status_code=404, detail="Plot not found")
    return PlotRead.model_validate(row)


@router.delete(
    "/projects/{project_id}/plots/{plot_id}",
    status_code=204,
)
async def delete_plot(
    project_id: str,
    plot_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> None:
    repo = SqlitePlotRepository(session)
    row = await repo.get(plot_id, user_id)
    if row is None or row.project_id != project_id:
        raise HTTPException(status_code=404, detail="Plot not found")
    await repo.delete(plot_id, user_id)
    return None


@router.post(
    "/projects/{project_id}/plots/{plot_id}/regenerate",
    response_model=PlotRead,
)
async def regenerate_plot(
    project_id: str,
    plot_id: str,
    container: Container = Depends(get_container),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> PlotRead:
    repo = SqlitePlotRepository(session)
    row = await repo.get(plot_id, user_id)
    if row is None or row.project_id != project_id:
        raise HTTPException(status_code=404, detail="Plot not found")
    dataset = await SqliteDatasetRepository(session).get(row.dataset_id, user_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    try:
        df = await _load_df(container, session, dataset, user_id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=f"Failed to load dataset: {exc}") from None
    try:
        data_uri = _render_to_uri(df, dict(row.spec))
    except PlotRenderError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    updated = await repo.update_png(
        plot_id=plot_id, png_data_uri=data_uri, user_id=user_id
    )
    assert updated is not None
    return PlotRead.model_validate(updated)
