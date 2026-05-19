"""Phase 13 (MP13) — Cross-dataset op endpoint.

POST /api/projects/{project_id}/datasets/cross-op

Body: {op, source_dataset_ids, args}.

Loads every source dataset (no transformations replayed — the user works on
raw data here), executes the op, persists the result as a new CSV via the
storage backend, and registers a new Dataset row tagged with
``derived_from_dataset_ids = source_dataset_ids``.
"""
from __future__ import annotations

import io
import logging
from collections.abc import AsyncIterator

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..container import Container, get_container
from ..db.models import Dataset, new_id
from ..repositories.datasets import SqliteDatasetRepository
from ..repositories.projects import SqliteProjectRepository
from ..schemas.cross_dataset import CrossOpRequest, CrossOpResponse
from ..services.stats.cross_dataset import (
    CrossDatasetError,
    append as op_append,
    join as op_join,
    merge as op_merge,
)
from ..services.stats.ingest import infer_columns, read_table

router = APIRouter(tags=["cross-dataset"])
log = logging.getLogger("research_api.cross_dataset")


async def _session(
    container: Container = Depends(get_container),
) -> AsyncIterator[AsyncSession]:
    async with container.session_factory() as s:
        yield s


def _user_id(container: Container = Depends(get_container)) -> str:
    return container.settings.local_user_id


async def _load_df(container: Container, dataset: Dataset) -> pd.DataFrame:
    from ..services.storage import StorageRef

    ref = StorageRef(backend=dataset.file_ref["backend"], key=dataset.file_ref["key"])
    data = await container.storage.read(ref)
    return read_table(data, dataset.file_type)


@router.post(
    "/projects/{project_id}/datasets/cross-op",
    response_model=CrossOpResponse,
    status_code=201,
)
async def cross_dataset_op(
    project_id: str,
    body: CrossOpRequest,
    container: Container = Depends(get_container),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> CrossOpResponse:
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    repo = SqliteDatasetRepository(session)

    # Per-op source count validation.
    if body.op in ("merge", "join"):
        if len(body.source_dataset_ids) != 2:
            raise HTTPException(
                status_code=422,
                detail=f"{body.op} requires exactly 2 source_dataset_ids",
            )
    elif body.op == "append":
        if len(body.source_dataset_ids) < 2:
            raise HTTPException(
                status_code=422,
                detail="append requires at least 2 source_dataset_ids",
            )

    sources: list[Dataset] = []
    for sid in body.source_dataset_ids:
        ds = await repo.get(sid, user_id)
        if ds is None or ds.project_id != project_id:
            raise HTTPException(
                status_code=404,
                detail=f"Source dataset {sid!r} not found in this project",
            )
        sources.append(ds)

    # Load all source frames.
    try:
        frames = [await _load_df(container, ds) for ds in sources]
    except Exception as exc:  # noqa: BLE001
        log.warning("Cross-op load failed: %s", exc)
        raise HTTPException(
            status_code=422, detail="Could not read one or more source datasets"
        ) from None

    # Execute op.
    try:
        if body.op == "merge":
            on = body.args.get("on")
            how = body.args.get("how", "inner")
            if not isinstance(on, list) or not on:
                raise CrossDatasetError("merge requires args.on as a non-empty list")
            result = op_merge(frames[0], frames[1], on=on, how=how)
        elif body.op == "append":
            result = op_append(*frames)
        elif body.op == "join":
            on = body.args.get("on")
            how = body.args.get("how", "left")
            if not isinstance(on, str) or not on:
                raise CrossDatasetError("join requires args.on as a string column")
            result = op_join(frames[0], frames[1], on=on, how=how)
        else:
            raise CrossDatasetError(f"unknown op {body.op!r}")
    except CrossDatasetError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None

    if result.empty:
        # Allowed (e.g. inner-merge with no overlap) but flagged.
        log.info("Cross-op produced an empty result: op=%s sources=%s", body.op, body.source_dataset_ids)

    # Persist as a new CSV.
    filename = body.filename
    if not filename:
        joined = "_".join(ds.filename.replace(".csv", "") for ds in sources)
        filename = f"{body.op}_{joined}.csv"
    if not filename.endswith(".csv"):
        filename += ".csv"

    buf = io.StringIO()
    result.to_csv(buf, index=False)
    csv_bytes = buf.getvalue().encode("utf-8")
    new_ref = await container.storage.save(
        user_id, "datasets", filename, csv_bytes
    )

    inferred = infer_columns(result)

    # We persist via the existing repo.create() but then patch
    # derived_from_dataset_ids in a single round-trip.
    new_ds = Dataset(
        id=new_id(),
        user_id=user_id,
        project_id=project_id,
        filename=filename,
        file_ref={"backend": new_ref.backend, "key": new_ref.key},
        file_type="text/csv",
        n_rows=int(result.shape[0]),
        n_columns=int(result.shape[1]),
        derived_from_dataset_ids=list(body.source_dataset_ids),
    )
    session.add(new_ds)
    await session.flush()

    from ..db.models import DatasetVariable

    for col in inferred:
        session.add(DatasetVariable(
            id=new_id(),
            user_id=user_id,
            dataset_id=new_ds.id,
            name=col.name,
            position=col.position,
            inferred_type=col.inferred_type,
            user_type=None,
            n_missing=col.n_missing,
            sample_values=list(col.sample_values),
        ))
    await session.commit()
    await session.refresh(new_ds)

    return CrossOpResponse(
        dataset_id=new_ds.id,
        filename=filename,
        n_rows=int(result.shape[0]),
        n_columns=int(result.shape[1]),
        source_dataset_ids=list(body.source_dataset_ids),
    )
