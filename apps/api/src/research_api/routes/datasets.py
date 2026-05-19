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
from ..services.stats.ingest import (
    XLSX_MIME,
    detect_table_mime,
    ingest,
    list_xlsx_sheets,
)

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

    # Multi-sheet XLSX → one Dataset per sheet (sharing one file_ref via
    # dataset_metadata.sheet_name). For single-sheet XLSX or CSV, keep the
    # legacy single-dataset path so existing callers/tests stay green.
    sheets: list[str] = []
    if mime == XLSX_MIME:
        try:
            sheets = list_xlsx_sheets(data)
        except Exception:  # noqa: BLE001
            sheets = []

    ref = await container.storage.save(
        user_id, "datasets", file.filename or "upload", data
    )
    repo = SqliteDatasetRepository(session)
    base_filename = file.filename or "upload"

    if mime == XLSX_MIME and len(sheets) > 1:
        # Parse each sheet; skip blanks but keep deterministic order. The
        # first parseable sheet wins as the "primary" response — the FE
        # then fetches the list and renders all sheets.
        primary: object = None
        for sheet_name in sheets:
            try:
                result = ingest(data, mime, sheet_name=sheet_name)
            except Exception as exc:  # noqa: BLE001
                log.warning(
                    "Dataset ingest failed for sheet %r: %s", sheet_name, exc
                )
                continue
            if result.n_rows == 0 and result.n_columns == 0:
                continue
            sheet_metadata: dict[str, object] = {"sheet_name": sheet_name}
            if result.long_format_hint:
                sheet_metadata["long_format_hint"] = result.long_format_hint
            dataset = await repo.create(
                project_id=project_id,
                filename=f"{base_filename} · {sheet_name}",
                file_ref={"backend": ref.backend, "key": ref.key},
                file_type=mime,
                n_rows=result.n_rows,
                n_columns=result.n_columns,
                variables=result.columns,
                user_id=user_id,
                dataset_metadata=sheet_metadata,
            )
            if primary is None:
                primary = dataset
        if primary is None:
            raise HTTPException(
                status_code=422,
                detail="No parseable sheets found in workbook.",
            )
        return await _hydrate(primary, repo, user_id)

    # Single sheet (or CSV) — legacy path.
    try:
        result = ingest(data, mime)
    except Exception as exc:  # noqa: BLE001
        log.warning("Dataset ingest failed: %s", exc)
        raise HTTPException(status_code=422, detail=f"Could not parse table: {exc}") from None

    single_metadata: dict[str, object] | None = None
    if result.long_format_hint:
        single_metadata = {"long_format_hint": result.long_format_hint}
    if mime == XLSX_MIME and len(sheets) == 1:
        single_metadata = {**(single_metadata or {}), "sheet_name": sheets[0]}

    dataset = await repo.create(
        project_id=project_id,
        filename=base_filename,
        file_ref={"backend": ref.backend, "key": ref.key},
        file_type=mime,
        n_rows=result.n_rows,
        n_columns=result.n_columns,
        variables=result.columns,
        user_id=user_id,
        dataset_metadata=single_metadata,
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


@router.get(
    "/projects/{project_id}/datasets/{dataset_id}/data",
)
async def preview_dataset(
    project_id: str,
    dataset_id: str,
    offset: int = 0,
    limit: int = 50,
    container: Container = Depends(get_container),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> dict:
    """Return real dataset rows (post-transformation) for the editable grid.

    The grid was previously fed by ``DatasetVariable.sample_values`` which
    only carried 5 distinct values per column; that made a 120-row table
    look like a 5-row one. This endpoint hydrates the raw bytes through
    ``read_dataset`` + the transformation stack, then slices ``offset/limit``.
    """
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    repo = SqliteDatasetRepository(session)
    dataset = await repo.get(dataset_id, user_id)
    if dataset is None or dataset.project_id != project_id:
        raise HTTPException(status_code=404, detail="Dataset not found")

    if limit <= 0 or limit > 500:
        limit = 50
    if offset < 0:
        offset = 0

    from ..repositories.transformations import SqliteTransformationRepository
    from ..services.stats.ingest import read_dataset
    from ..services.stats.transform import apply_transformations
    from ..services.storage import StorageRef

    ref = StorageRef(
        backend=dataset.file_ref["backend"], key=dataset.file_ref["key"]
    )
    try:
        data = await container.storage.read(ref)
    except Exception as exc:  # noqa: BLE001
        log.warning("Dataset file unreadable: %s", exc)
        raise HTTPException(status_code=410, detail="Dataset file is missing") from None
    try:
        df = read_dataset(data, dataset)
    except Exception as exc:  # noqa: BLE001
        log.warning("Dataset parse failed: %s", exc)
        raise HTTPException(status_code=422, detail=f"Could not read dataset: {exc}") from None

    trepo = SqliteTransformationRepository(session)
    ops = await trepo.list_for_dataset(dataset_id, user_id)
    if ops:
        try:
            df = apply_transformations(
                df, [{"op_type": t.op_type, "op_args": t.op_args} for t in ops]
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("Transformation replay failed: %s", exc)
            # Don't 500 — show the pre-transform rows so the user can
            # inspect what's going wrong.
    n_rows = int(df.shape[0])
    sliced = df.iloc[offset : offset + limit]
    columns = [str(c) for c in df.columns]
    # Coerce every cell to a JSON-safe scalar. NaN / NaT → None, numpy
    # scalars unwrapped to native Python.
    import math

    import numpy as np

    def _coerce(v: object) -> object:
        if v is None:
            return None
        if isinstance(v, float) and math.isnan(v):
            return None
        if isinstance(v, (np.integer,)):
            return int(v)
        if isinstance(v, (np.floating,)):
            f = float(v)
            return None if math.isnan(f) else f
        if isinstance(v, np.bool_):
            return bool(v)
        if isinstance(v, (int, float, bool, str)):
            return v
        # pd.Timestamp etc.
        return str(v)

    rows_out: list[dict] = []
    for idx, row in sliced.iterrows():
        cells: dict[str, object] = {"__row_index": int(idx)}
        for c in columns:
            cells[c] = _coerce(row[c])
        rows_out.append(cells)
    return {
        "columns": columns,
        "rows": rows_out,
        "offset": offset,
        "limit": limit,
        "total": n_rows,
    }


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
