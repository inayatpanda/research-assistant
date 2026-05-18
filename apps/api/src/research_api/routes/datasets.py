"""Datasets routes: upload (CSV/XLSX) + list + read + variable override + delete."""
from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from ..container import Container, get_container
from ..repositories.datasets import SqliteDatasetRepository
from ..repositories.projects import SqliteProjectRepository
from ..schemas.dataset import (
    DatasetRead,
    DatasetVariableRead,
    DatasetVariableUpdate,
)
from ..services.stats.ingest import detect_table_mime, ingest

router = APIRouter(tags=["datasets"])
log = logging.getLogger("research_api.datasets")


async def _session(
    container: Container = Depends(get_container),
) -> AsyncIterator[AsyncSession]:
    async with container.session_factory() as s:
        yield s


def _user_id(container: Container = Depends(get_container)) -> str:
    return container.settings.local_user_id


async def _hydrate(
    dataset, repo: SqliteDatasetRepository, user_id: str
) -> DatasetRead:
    variables = await repo.list_variables(dataset.id, user_id)
    read = DatasetRead.model_validate(dataset)
    read.variables = [DatasetVariableRead.model_validate(v) for v in variables]
    return read


@router.post(
    "/projects/{project_id}/datasets",
    response_model=DatasetRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_dataset(
    project_id: str,
    file: Annotated[UploadFile, File(...)],
    container: Container = Depends(get_container),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> DatasetRead:
    settings = container.settings

    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(data) > settings.file_size_cap_mb * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds {settings.file_size_cap_mb} MB cap",
        )

    # Hard reject PDF and other non-table bytes via magic-byte sniff
    if data[:5] == b"%PDF-":
        raise HTTPException(status_code=415, detail="Unsupported MIME application/pdf")
    try:
        mime = detect_table_mime(data)
    except ValueError:
        raise HTTPException(
            status_code=415, detail="Unsupported MIME; expected CSV or XLSX"
        ) from None

    try:
        result = ingest(data, mime)
    except Exception as exc:  # noqa: BLE001
        log.warning("Dataset ingest failed: %s", exc)
        raise HTTPException(status_code=422, detail=f"Could not parse table: {exc}") from None

    ref = await container.storage.save(
        user_id, "datasets", file.filename or "upload", data
    )

    repo = SqliteDatasetRepository(session)
    dataset = await repo.create(
        project_id=project_id,
        filename=file.filename or "upload",
        file_ref={"backend": ref.backend, "key": ref.key},
        file_type=mime,
        n_rows=result.n_rows,
        n_columns=result.n_columns,
        variables=result.columns,
        user_id=user_id,
    )
    return await _hydrate(dataset, repo, user_id)


@router.get(
    "/projects/{project_id}/datasets",
    response_model=list[DatasetRead],
)
async def list_datasets(
    project_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> list[DatasetRead]:
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    repo = SqliteDatasetRepository(session)
    rows = await repo.list_for_project(project_id, user_id)
    return [await _hydrate(r, repo, user_id) for r in rows]


@router.get(
    "/projects/{project_id}/datasets/{dataset_id}",
    response_model=DatasetRead,
)
async def get_dataset(
    project_id: str,
    dataset_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> DatasetRead:
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    repo = SqliteDatasetRepository(session)
    dataset = await repo.get(dataset_id, user_id)
    if dataset is None or dataset.project_id != project_id:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return await _hydrate(dataset, repo, user_id)


@router.patch(
    "/projects/{project_id}/datasets/{dataset_id}/variables/{variable_id}",
    response_model=DatasetVariableRead,
)
async def update_variable(
    project_id: str,
    dataset_id: str,
    variable_id: str,
    body: DatasetVariableUpdate,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> DatasetVariableRead:
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    repo = SqliteDatasetRepository(session)
    dataset = await repo.get(dataset_id, user_id)
    if dataset is None or dataset.project_id != project_id:
        raise HTTPException(status_code=404, detail="Dataset not found")

    variables = await repo.list_variables(dataset_id, user_id)
    if variable_id not in {v.id for v in variables}:
        raise HTTPException(status_code=404, detail="Variable not found")

    updated = await repo.update_variable_type(
        variable_id=variable_id, user_type=body.user_type, user_id=user_id
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Variable not found")
    return DatasetVariableRead.model_validate(updated)


@router.delete(
    "/projects/{project_id}/datasets/{dataset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_dataset(
    project_id: str,
    dataset_id: str,
    container: Container = Depends(get_container),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> None:
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    repo = SqliteDatasetRepository(session)
    dataset = await repo.get(dataset_id, user_id)
    if dataset is None or dataset.project_id != project_id:
        raise HTTPException(status_code=404, detail="Dataset not found")

    if dataset.file_ref:
        from ..services.storage import StorageRef

        try:
            await container.storage.delete(
                StorageRef(backend=dataset.file_ref["backend"], key=dataset.file_ref["key"])
            )
        except Exception:
            pass
    await repo.delete(dataset_id, user_id)
    return None
