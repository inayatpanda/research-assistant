"""Phase 13 — Propensity-score matching endpoint.

POST /api/projects/{project_id}/datasets/{dataset_id}/psm

Fits logistic-regression propensity scores, performs 1:1 nearest-neighbour
matching with caliper, computes pre/post covariate balance, and persists
the matched subset as a NEW Dataset row linked to the source via
``derived_from_dataset_id``. The covariate-balance JSON is stored on the
new dataset's ``dataset_metadata`` column.
"""
from __future__ import annotations

import io
import logging
import math
from collections.abc import AsyncIterator

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..container import Container, get_container
from ..repositories.datasets import SqliteDatasetRepository
from ..repositories.projects import SqliteProjectRepository
from ..schemas.psm import CovariateBalanceRow, PSMRequest, PSMResponse
from ..services.stats.ingest import infer_columns, read_table
from ..services.stats.psm import run_psm

router = APIRouter(tags=["psm"])
log = logging.getLogger("research_api.psm")


async def _session(
    container: Container = Depends(get_container),
) -> AsyncIterator[AsyncSession]:
    async with container.session_factory() as s:
        yield s


def _user_id(container: Container = Depends(get_container)) -> str:
    return container.settings.local_user_id


def _safe_float(x: float) -> float:
    return float(x) if math.isfinite(float(x)) else 0.0


def _df_to_rows(df: pd.DataFrame) -> list[CovariateBalanceRow]:
    return [
        CovariateBalanceRow(
            covariate=str(row["covariate"]),
            smd=_safe_float(row["smd"]),
            mean_treated=_safe_float(row["mean_treated"]),
            mean_control=_safe_float(row["mean_control"]),
        )
        for row in df.to_dict(orient="records")
    ]


def _max_smd(df: pd.DataFrame) -> float:
    if df.empty:
        return 0.0
    return _safe_float(df["smd"].max())


@router.post(
    "/projects/{project_id}/datasets/{dataset_id}/psm",
    response_model=PSMResponse,
)
async def run_psm_endpoint(
    project_id: str,
    dataset_id: str,
    body: PSMRequest,
    container: Container = Depends(get_container),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> PSMResponse:
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    repo = SqliteDatasetRepository(session)
    source = await repo.get(dataset_id, user_id)
    if source is None or source.project_id != project_id:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Validate that the requested columns exist on the source dataset.
    variables = await repo.list_variables(dataset_id, user_id)
    allowed = {v.name for v in variables}
    if body.treatment_col not in allowed:
        raise HTTPException(
            status_code=422,
            detail=f"treatment_col {body.treatment_col!r} is not a column of this dataset",
        )
    bad = [c for c in body.covariate_cols if c not in allowed]
    if bad:
        raise HTTPException(
            status_code=422,
            detail=f"covariate_cols not in dataset: {bad!r}",
        )
    if body.treatment_col in body.covariate_cols:
        raise HTTPException(
            status_code=422,
            detail="treatment_col must not appear in covariate_cols",
        )

    # Load + run.
    try:
        from ..services.storage import StorageRef

        ref = StorageRef(
            backend=source.file_ref["backend"], key=source.file_ref["key"]
        )
        data = await container.storage.read(ref)
        df = read_table(data, source.file_type)
    except Exception as exc:  # noqa: BLE001
        log.warning("PSM source dataset unreadable: %s", exc)
        raise HTTPException(status_code=422, detail="Could not read source dataset") from None

    try:
        result = run_psm(
            df,
            treatment_col=body.treatment_col,
            covariate_cols=list(body.covariate_cols),
            caliper_sd_multiplier=body.caliper_sd,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None

    matched_df: pd.DataFrame = result["matched_df"]  # type: ignore[assignment]
    if matched_df.empty:
        raise HTTPException(
            status_code=422,
            detail="No matched pairs survive the caliper; loosen caliper_sd or check covariates.",
        )

    # Persist the matched subset as a new CSV via the storage backend.
    buf = io.StringIO()
    matched_df.to_csv(buf, index=False)
    csv_bytes = buf.getvalue().encode("utf-8")
    matched_filename = f"psm_matched_from_{source.filename}"
    if not matched_filename.endswith(".csv"):
        matched_filename += ".csv"

    new_ref = await container.storage.save(
        user_id, "datasets", matched_filename, csv_bytes
    )

    inferred = infer_columns(matched_df)

    balance_before_df: pd.DataFrame = result["balance_before"]  # type: ignore[assignment]
    balance_after_df: pd.DataFrame = result["balance_after"]  # type: ignore[assignment]

    metadata = {
        "psm": {
            "source_dataset_id": dataset_id,
            "treatment_col": body.treatment_col,
            "covariate_cols": list(body.covariate_cols),
            "caliper_sd": body.caliper_sd,
            "n_treated_total": int(result["n_treated_total"]),
            "n_control_total": int(result["n_control_total"]),
            "n_treated_matched": int(result["n_treated_matched"]),
            "n_control_matched": int(result["n_control_matched"]),
            "balance_before": balance_before_df.to_dict(orient="records"),
            "balance_after": balance_after_df.to_dict(orient="records"),
            "max_smd_before": _max_smd(balance_before_df),
            "max_smd_after": _max_smd(balance_after_df),
        }
    }

    new_dataset = await repo.create_derived(
        project_id=project_id,
        filename=matched_filename,
        file_ref={"backend": new_ref.backend, "key": new_ref.key},
        file_type="text/csv",
        n_rows=int(matched_df.shape[0]),
        n_columns=int(matched_df.shape[1]),
        variables=inferred,
        user_id=user_id,
        derived_from_dataset_id=dataset_id,
        dataset_metadata=metadata,
    )

    return PSMResponse(
        matched_dataset_id=new_dataset.id,
        n_treated_total=int(result["n_treated_total"]),
        n_control_total=int(result["n_control_total"]),
        n_treated_matched=int(result["n_treated_matched"]),
        n_control_matched=int(result["n_control_matched"]),
        caliper_sd=body.caliper_sd,
        balance_before=_df_to_rows(balance_before_df),
        balance_after=_df_to_rows(balance_after_df),
        max_smd_before=_max_smd(balance_before_df),
        max_smd_after=_max_smd(balance_after_df),
    )
