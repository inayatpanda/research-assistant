"""Phase 8.7 — Figures routes: upload, list, get-binary, patch, reorder, delete."""
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..container import Container, get_container
from ..db.models import Figure
from ..repositories.figures import SqliteFigureRepository
from ..repositories.projects import SqliteProjectRepository
from ..schemas.figure import FigureRead, FigureReorderRequest, FigureUpdate
from ..services.figures.validation import (
    FIGURE_SIZE_CAP_MB,
    FigureValidationError,
    validate_image_bytes,
)
from ..services.storage import StorageRef


router = APIRouter(tags=["figures"])


async def _session(
    container: Container = Depends(get_container),
) -> AsyncIterator[AsyncSession]:
    async with container.session_factory() as s:
        yield s


def _user_id(container: Container = Depends(get_container)) -> str:
    return container.settings.local_user_id


async def _hydrate(orm: Figure, container: Container) -> FigureRead:
    read = FigureRead.model_validate(orm)
    try:
        ref = StorageRef(backend=orm.file_ref["backend"], key=orm.file_ref["key"])
        read.file_url = await container.storage.signed_url(ref, expires_in=3600)
    except Exception:  # storage offline — let the client retry the signed URL
        read.file_url = None
    return read


@router.post(
    "/projects/{project_id}/figures",
    response_model=FigureRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_figure(
    project_id: str,
    file: Annotated[UploadFile, File(...)],
    container: Container = Depends(get_container),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> FigureRead:
    proj_repo = SqliteProjectRepository(session)
    proj = await proj_repo.get(project_id, user_id)
    if proj is None:
        raise HTTPException(status_code=404, detail="Project not found")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(data) > FIGURE_SIZE_CAP_MB * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds {FIGURE_SIZE_CAP_MB} MiB cap",
        )

    try:
        validated = validate_image_bytes(data)
    except FigureValidationError as e:
        raise HTTPException(status_code=415, detail=str(e)) from e

    ref = await container.storage.save(
        user_id, "figures", file.filename or "figure", data
    )

    repo = SqliteFigureRepository(session)
    fig = await repo.create(
        project_id=project_id,
        user_id=user_id,
        file_ref={"backend": ref.backend, "key": ref.key},
        file_type=validated.mime,
        width_px=validated.width_px,
        height_px=validated.height_px,
        byte_size=validated.byte_size,
    )
    return await _hydrate(fig, container)


@router.get(
    "/projects/{project_id}/figures",
    response_model=list[FigureRead],
)
async def list_figures(
    project_id: str,
    container: Container = Depends(get_container),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> list[FigureRead]:
    proj_repo = SqliteProjectRepository(session)
    proj = await proj_repo.get(project_id, user_id)
    if proj is None:
        raise HTTPException(status_code=404, detail="Project not found")
    repo = SqliteFigureRepository(session)
    rows = await repo.list(project_id=project_id, user_id=user_id)
    return [await _hydrate(r, container) for r in rows]


@router.get("/figures/{figure_id}", response_model=FigureRead)
async def get_figure(
    figure_id: str,
    container: Container = Depends(get_container),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> FigureRead:
    repo = SqliteFigureRepository(session)
    fig = await repo.get(figure_id, user_id)
    if fig is None:
        raise HTTPException(status_code=404, detail="Figure not found")
    return await _hydrate(fig, container)


@router.patch("/figures/{figure_id}", response_model=FigureRead)
async def update_figure(
    figure_id: str,
    patch: FigureUpdate,
    container: Container = Depends(get_container),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> FigureRead:
    repo = SqliteFigureRepository(session)
    updated = await repo.update(
        figure_id, user_id, caption=patch.caption, alt_text=patch.alt_text
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Figure not found")
    return await _hydrate(updated, container)


@router.post(
    "/projects/{project_id}/figures/reorder",
    response_model=list[FigureRead],
)
async def reorder_figures(
    project_id: str,
    body: FigureReorderRequest,
    container: Container = Depends(get_container),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> list[FigureRead]:
    proj_repo = SqliteProjectRepository(session)
    proj = await proj_repo.get(project_id, user_id)
    if proj is None:
        raise HTTPException(status_code=404, detail="Project not found")
    repo = SqliteFigureRepository(session)
    try:
        rows = await repo.reorder(
            project_id=project_id, user_id=user_id, ordered_ids=body.ordered_figure_ids
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return [await _hydrate(r, container) for r in rows]


@router.delete("/figures/{figure_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_figure(
    figure_id: str,
    container: Container = Depends(get_container),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> None:
    repo = SqliteFigureRepository(session)
    deleted = await repo.delete(figure_id, user_id)
    if deleted is None:
        raise HTTPException(status_code=404, detail="Figure not found")
    # Evict the file from storage. Best-effort — the row is already gone.
    if deleted.file_ref:
        try:
            await container.storage.delete(
                StorageRef(backend=deleted.file_ref["backend"], key=deleted.file_ref["key"])
            )
        except Exception:
            pass
    return None
