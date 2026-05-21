"""Phase 13 (MP13) — DatasetTransformation routes.

Endpoints (under /api/projects/{project_id}/datasets/{dataset_id}/transformations):

  GET    /                       list (in position order)
  POST   /                       add (optional 'position' for insert)
  PATCH  /{transformation_id}    update args / label / position
  DELETE /{transformation_id}    delete (gaps are densified)
  POST   /reorder                replace_all by exact id sequence

The runner replays the dataset's transformation stack before every analysis,
so the user's view of the data here is identical to what tests run against.
"""
from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..container import Container, get_container
from ..auth_deps import get_current_user
from ..schemas.auth import UserRead
from ..repositories.datasets import SqliteDatasetRepository
from ..repositories.projects import SqliteProjectRepository
from ..repositories.transformations import SqliteTransformationRepository
from ..schemas.transformation import (
    TransformationCreate,
    TransformationRead,
    TransformationReorderRequest,
    TransformationUpdate,
)
from ..services.stats.transform import OP_TYPES

router = APIRouter(tags=["transformations"])


# DEMO-FIX-D HIGH-3 — Per-op-type column-type contracts. Keys are the op
# types that REQUIRE specific column dtypes; values are the set of
# user-facing type names (matching ``DatasetVariable.inferred_type`` /
# ``user_type``) that the target column must satisfy. We validate at
# op-add time so the UI surfaces a precise 422 instead of an opaque
# runner-time failure deep inside numpy.
OP_REQUIRED_TYPES: dict[str, set[str]] = {
    "log_transform": {"numeric"},
    "z_score": {"numeric"},
}

# Pretty labels for error prose.
_TYPE_LABELS = {
    "numeric": "Numeric",
    "nominal": "Nominal",
    "ordinal": "Ordinal",
    "time": "Time",
}


def _validate_op_column_types(
    op_type: str, op_args: dict, variables: list
) -> None:
    """Reject numeric-only ops applied to non-numeric columns at op-add time.

    Raises HTTPException(422) with a user-readable message naming the column
    and its current type. No-op for ops that have no type contract.
    """
    required = OP_REQUIRED_TYPES.get(op_type)
    if not required:
        return
    col_name = (op_args or {}).get("column")
    if not isinstance(col_name, str):
        return  # let downstream structural validation catch this
    type_by_name = {
        v.name: (v.user_type or v.inferred_type) for v in variables
    }
    actual = type_by_name.get(col_name)
    if actual is None:
        # Unknown column — let the runner raise on apply; we don't want to
        # block ops that reference yet-to-be-created columns (e.g. created
        # by an earlier mutate op).
        return
    if actual not in required:
        pretty_op = op_type.replace("_", " ").capitalize()
        pretty_actual = _TYPE_LABELS.get(actual, actual)
        raise HTTPException(
            status_code=422,
            detail=(
                f"{pretty_op} requires a numeric column; "
                f"{col_name!r} is {pretty_actual}."
            ),
        )


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
) -> None:
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    ds = await SqliteDatasetRepository(session).get(dataset_id, user_id)
    if ds is None or ds.project_id != project_id:
        raise HTTPException(status_code=404, detail="Dataset not found")


@router.get(
    "/projects/{project_id}/datasets/{dataset_id}/transformations",
    response_model=list[TransformationRead],
)
async def list_transformations(
    project_id: str,
    dataset_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> list[TransformationRead]:
    await _require_dataset(session, project_id, dataset_id, user_id)
    repo = SqliteTransformationRepository(session)
    rows = await repo.list_for_dataset(dataset_id, user_id)
    return [TransformationRead.model_validate(r) for r in rows]


@router.post(
    "/projects/{project_id}/datasets/{dataset_id}/transformations",
    response_model=TransformationRead,
    status_code=201,
)
async def create_transformation(
    project_id: str,
    dataset_id: str,
    body: TransformationCreate,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> TransformationRead:
    await _require_dataset(session, project_id, dataset_id, user_id)
    if body.op_type not in OP_TYPES:
        raise HTTPException(status_code=422, detail=f"Unknown op_type {body.op_type!r}")
    # DEMO-FIX-D HIGH-3 — Reject numeric-only ops on non-numeric columns up
    # front so users see a precise message instead of an opaque runner crash.
    variables = await SqliteDatasetRepository(session).list_variables(
        dataset_id, user_id
    )
    _validate_op_column_types(body.op_type, body.op_args or {}, variables)
    repo = SqliteTransformationRepository(session)
    row = await repo.create(
        dataset_id=dataset_id,
        user_id=user_id,
        op_type=body.op_type,
        op_args=body.op_args,
        label=body.label,
        position=body.position,
    )
    return TransformationRead.model_validate(row)


@router.patch(
    "/projects/{project_id}/datasets/{dataset_id}/transformations/{transformation_id}",
    response_model=TransformationRead,
)
async def update_transformation(
    project_id: str,
    dataset_id: str,
    transformation_id: str,
    body: TransformationUpdate,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> TransformationRead:
    await _require_dataset(session, project_id, dataset_id, user_id)
    repo = SqliteTransformationRepository(session)
    row = await repo.get(transformation_id, user_id)
    if row is None or row.dataset_id != dataset_id:
        raise HTTPException(status_code=404, detail="Transformation not found")
    # DEMO-FIX-D HIGH-3 — also re-validate on PATCH so editing an existing
    # op to target a non-numeric column raises the same precise 422.
    if body.op_args is not None:
        variables = await SqliteDatasetRepository(session).list_variables(
            dataset_id, user_id
        )
        _validate_op_column_types(row.op_type, body.op_args or {}, variables)
    updated = await repo.update(
        transformation_id=transformation_id,
        user_id=user_id,
        op_args=body.op_args,
        label=body.label,
        position=body.position,
    )
    assert updated is not None
    return TransformationRead.model_validate(updated)


@router.delete(
    "/projects/{project_id}/datasets/{dataset_id}/transformations/{transformation_id}",
    status_code=204,
)
async def delete_transformation(
    project_id: str,
    dataset_id: str,
    transformation_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> None:
    await _require_dataset(session, project_id, dataset_id, user_id)
    repo = SqliteTransformationRepository(session)
    row = await repo.get(transformation_id, user_id)
    if row is None or row.dataset_id != dataset_id:
        raise HTTPException(status_code=404, detail="Transformation not found")
    await repo.delete(transformation_id, user_id)
    return None


@router.post(
    "/projects/{project_id}/datasets/{dataset_id}/transformations/reorder",
    response_model=list[TransformationRead],
)
async def reorder_transformations(
    project_id: str,
    dataset_id: str,
    body: TransformationReorderRequest,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> list[TransformationRead]:
    await _require_dataset(session, project_id, dataset_id, user_id)
    repo = SqliteTransformationRepository(session)
    try:
        rows = await repo.replace_all(
            dataset_id=dataset_id, user_id=user_id, ordered_ids=body.ids
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return [TransformationRead.model_validate(r) for r in rows]
