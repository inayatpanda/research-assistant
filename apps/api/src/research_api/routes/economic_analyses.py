"""Phase 18 (MP18) — Health Economics routes.

Endpoints (all project- and user-scoped):

  POST   /api/projects/{pid}/economic-analyses                  create
  GET    /api/projects/{pid}/economic-analyses                  list
  GET    /api/projects/{pid}/economic-analyses/{id}             get
  PATCH  /api/projects/{pid}/economic-analyses/{id}             update
  POST   /api/projects/{pid}/economic-analyses/{id}/run         run end-to-end
  POST   /api/projects/{pid}/economic-analyses/{id}/sensitivity   PSA/DSA/scenario
  POST   /api/projects/{pid}/economic-analyses/{id}/interpret   AI prose
  POST   /api/projects/{pid}/economic-analyses/{id}/push        push to manuscript
  GET    /api/projects/{pid}/economic-analyses/{id}/cheers-report?format=docx|pdf
  DELETE /api/projects/{pid}/economic-analyses/{id}             delete

Plus a sibling endpoint:
  GET    /api/utility-value-sets                                static catalogue

Pattern mirrors ``routes/analyses.py``: every endpoint validates that the
project belongs to the caller (via ``SqliteProjectRepository.get``) before
delegating to ``SqliteEconomicAnalysisRepository``, which already filters
by ``user_id``.
"""
from __future__ import annotations

import io
import logging
from collections.abc import AsyncIterator
from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..container import Container, get_container
from ..db.models import Dataset, EconomicAnalysis
from ..repositories.datasets import SqliteDatasetRepository
from ..repositories.economics import (
    SqliteEconomicAnalysisRepository,
    SqliteEconomicResultRepository,
)
from ..repositories.manuscript_sections import SqliteManuscriptSectionRepository
from ..repositories.projects import SqliteProjectRepository
from ..schemas.economics import (
    EconomicAnalysisCreate,
    EconomicAnalysisRead,
    EconomicAnalysisUpdate,
    EconomicResultRead,
    PushEconomicRequest,
    SensitivityKind,
    SensitivityRequest,
    UtilityValueSetInfo,
)
from ..schemas.manuscript_section import ManuscriptSectionRead
from ..services.ai import (
    AIError,
    AIProviderUnavailable,
    AIRateLimited,
    AISourceInsufficient,
)
from ..services.citation_format import (
    CitationStyle,
    replace_cite_tokens_with_markup,
)
from ..services.economics.ceac import build_ceac
from ..services.economics.charts import (
    png_to_data_uri,
    render_ce_plane,
    render_ceac,
    render_tornado,
)
from ..services.economics.cost_qaly_regression import bivariate_bootstrap
from ..services.economics.icer import compute_icer, nmb_at_thresholds
from ..services.economics.qaly import compute_qaly
from ..services.economics.sensitivity import dsa, psa, scenario
from ..services.economics.utility_value_sets import catalogue
from ..services.export.economic_report import CHEERSContext, build_economic_report
from .reviews import _BLOCK_TAG_BY_CLASS, _push_to_section

router = APIRouter(tags=["economic-analyses"])
log = logging.getLogger("research_api.economic_analyses")


# ─── Class hook registration ──────────────────────────────────────────────
_BLOCK_TAG_BY_CLASS.setdefault("economic-analysis", "figure")


async def _session(
    container: Container = Depends(get_container),
) -> AsyncIterator[AsyncSession]:
    async with container.session_factory() as s:
        yield s


def _user_id(container: Container = Depends(get_container)) -> str:
    return container.settings.local_user_id


async def _load_dataframe(container: Container, dataset: Dataset) -> pd.DataFrame:
    from ..services.storage import StorageRef
    from ..services.stats.ingest import read_dataset

    ref = StorageRef(backend=dataset.file_ref["backend"], key=dataset.file_ref["key"])
    data = await container.storage.read(ref)
    return read_dataset(data, dataset)


def _map_ai_error(e: Exception) -> HTTPException:
    log.warning("AI error: %s: %s", type(e).__name__, e)
    if isinstance(e, AIRateLimited):
        return HTTPException(status_code=429, detail="AI rate limited")
    if isinstance(e, AISourceInsufficient):
        return HTTPException(
            status_code=422, detail="insufficient input to interpret result"
        )
    return HTTPException(status_code=503, detail="AI provider unavailable")


def _hydrate(
    analysis: EconomicAnalysis, result: Any | None
) -> EconomicAnalysisRead:
    read = EconomicAnalysisRead.model_validate(analysis)
    if result is not None:
        read.result = EconomicResultRead.model_validate(result)
    return read


# ─── Utility value-set catalogue (no project scope — static) ──────────────


@router.get(
    "/utility-value-sets",
    response_model=list[UtilityValueSetInfo],
)
async def list_utility_value_sets() -> list[UtilityValueSetInfo]:
    return [UtilityValueSetInfo(**c) for c in catalogue()]


# ─── CRUD ──────────────────────────────────────────────────────────────────


@router.post(
    "/projects/{project_id}/economic-analyses",
    response_model=EconomicAnalysisRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_economic_analysis(
    project_id: str,
    body: EconomicAnalysisCreate,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> EconomicAnalysisRead:
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    # If the user supplied a dataset_id, verify ownership.
    if body.dataset_id:
        ds = await SqliteDatasetRepository(session).get(body.dataset_id, user_id)
        if ds is None or ds.project_id != project_id:
            raise HTTPException(status_code=404, detail="Dataset not found")

    repo = SqliteEconomicAnalysisRepository(session)
    row = await repo.create(
        project_id=project_id,
        user_id=user_id,
        dataset_id=body.dataset_id,
        name=body.name,
        currency=body.currency,
        time_horizon_months=body.time_horizon_months,
        perspective=body.perspective,
        discount_rate_costs=body.discount_rate_costs,
        discount_rate_qalys=body.discount_rate_qalys,
        wtp_thresholds=body.wtp_thresholds,
        utility_value_set=body.utility_value_set,
        bootstrap_n=body.bootstrap_n,
        seed=body.seed,
        treatment_col=body.treatment_col,
        comparator_label=body.comparator_label,
        intervention_label=body.intervention_label,
        cost_columns=[c.model_dump() for c in body.cost_columns],
    )
    return _hydrate(row, None)


@router.get(
    "/projects/{project_id}/economic-analyses",
    response_model=list[EconomicAnalysisRead],
)
async def list_economic_analyses(
    project_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> list[EconomicAnalysisRead]:
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    repo = SqliteEconomicAnalysisRepository(session)
    res_repo = SqliteEconomicResultRepository(session)
    rows = await repo.list_for_project(project_id, user_id)
    out: list[EconomicAnalysisRead] = []
    for r in rows:
        result = await res_repo.get_for_analysis(r.id, user_id)
        out.append(_hydrate(r, result))
    return out


@router.get(
    "/projects/{project_id}/economic-analyses/{analysis_id}",
    response_model=EconomicAnalysisRead,
)
async def get_economic_analysis(
    project_id: str,
    analysis_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> EconomicAnalysisRead:
    repo = SqliteEconomicAnalysisRepository(session)
    row = await repo.get(analysis_id, user_id)
    if row is None or row.project_id != project_id:
        raise HTTPException(status_code=404, detail="Economic analysis not found")
    res_repo = SqliteEconomicResultRepository(session)
    result = await res_repo.get_for_analysis(analysis_id, user_id)
    return _hydrate(row, result)


@router.patch(
    "/projects/{project_id}/economic-analyses/{analysis_id}",
    response_model=EconomicAnalysisRead,
)
async def update_economic_analysis(
    project_id: str,
    analysis_id: str,
    body: EconomicAnalysisUpdate,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> EconomicAnalysisRead:
    repo = SqliteEconomicAnalysisRepository(session)
    row = await repo.get(analysis_id, user_id)
    if row is None or row.project_id != project_id:
        raise HTTPException(status_code=404, detail="Economic analysis not found")
    patch = body.model_dump(exclude_unset=True, exclude_none=True)
    # Re-serialise cost_columns from the validated BaseModel list
    if "cost_columns" in patch and patch["cost_columns"] is not None:
        patch["cost_columns"] = [
            c.model_dump() if hasattr(c, "model_dump") else c
            for c in patch["cost_columns"]
        ]
    updated = await repo.update(
        analysis_id=analysis_id, user_id=user_id, patch=patch
    )
    res_repo = SqliteEconomicResultRepository(session)
    result = await res_repo.get_for_analysis(analysis_id, user_id)
    return _hydrate(updated, result)  # type: ignore[arg-type]


@router.delete(
    "/projects/{project_id}/economic-analyses/{analysis_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_economic_analysis(
    project_id: str,
    analysis_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> None:
    repo = SqliteEconomicAnalysisRepository(session)
    row = await repo.get(analysis_id, user_id)
    if row is None or row.project_id != project_id:
        raise HTTPException(status_code=404, detail="Economic analysis not found")
    await repo.delete(analysis_id, user_id)
    return None


# ─── Run ───────────────────────────────────────────────────────────────────


def _resolve_cost_qaly_cols(
    analysis: EconomicAnalysis,
) -> tuple[str | None, str | None, str | None, str | None]:
    """Pick out (cost_col, qaly_col, utility_col, time_col) from cost_columns."""
    cost_col: str | None = None
    qaly_col: str | None = None
    utility_col: str | None = None
    time_col: str | None = None
    for entry in (analysis.cost_columns or []):
        role = entry.get("role")
        col = entry.get("col")
        if role == "cost_total" and col:
            cost_col = col
        elif role == "qaly_weight" and col:
            qaly_col = col
        elif role == "utility_score" and col:
            utility_col = col
        elif role == "time_to_event" and col:
            time_col = col
    return cost_col, qaly_col, utility_col, time_col


@router.post(
    "/projects/{project_id}/economic-analyses/{analysis_id}/run",
    response_model=EconomicAnalysisRead,
)
async def run_economic_analysis(
    project_id: str,
    analysis_id: str,
    container: Container = Depends(get_container),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> EconomicAnalysisRead:
    repo = SqliteEconomicAnalysisRepository(session)
    pair = await repo.get_with_dataset(analysis_id, user_id)
    if pair is None:
        raise HTTPException(status_code=404, detail="Economic analysis not found")
    analysis, dataset = pair
    if analysis.project_id != project_id:
        raise HTTPException(status_code=404, detail="Economic analysis not found")
    if dataset is None:
        raise HTTPException(
            status_code=422, detail="Economic analysis has no dataset bound"
        )

    cost_col, qaly_col, utility_col, time_col = _resolve_cost_qaly_cols(analysis)
    if not cost_col:
        raise HTTPException(
            status_code=422,
            detail="cost_columns must include a binding with role='cost_total'",
        )

    try:
        df = await _load_dataframe(container, dataset)
    except Exception as exc:  # noqa: BLE001
        log.warning("Failed to load dataset bytes: %s", exc)
        raise HTTPException(status_code=422, detail="Could not load dataset") from None

    # Derive QALYs if no direct qaly_weight column was bound but a utility
    # series + time-to-event column are available.
    if not qaly_col:
        if utility_col and time_col:
            try:
                # Use the dataset row id (index) as patient_col fallback.
                df["_patient_idx_"] = df.get(
                    "patient_id", pd.Series(df.index, index=df.index)
                )
                qaly_df = compute_qaly(
                    df,
                    utility_col=utility_col,
                    time_col=time_col,
                    patient_col="_patient_idx_",
                    group_col=analysis.treatment_col,
                    baseline_adjust=True,
                )
                # Merge QALYs back so the downstream regression has both.
                df = df.merge(
                    qaly_df[["_patient_idx_", "qaly"]], on="_patient_idx_", how="left"
                )
                qaly_col = "qaly"
            except Exception as exc:  # noqa: BLE001
                raise HTTPException(
                    status_code=422,
                    detail=f"QALY derivation failed: {exc}",
                ) from None
        else:
            raise HTTPException(
                status_code=422,
                detail=(
                    "cost_columns must include a 'qaly_weight' column OR both "
                    "'utility_score' + 'time_to_event' for AUC QALY derivation"
                ),
            )

    try:
        boot = bivariate_bootstrap(
            df,
            cost_col=cost_col,
            qaly_col=qaly_col,
            treatment_col=analysis.treatment_col,
            intervention_label=analysis.intervention_label,
            comparator_label=analysis.comparator_label,
            n_boot=int(analysis.bootstrap_n),
            seed=int(analysis.seed),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None

    icer_res = compute_icer(boot["mean_cost_diff"], boot["mean_qaly_diff"])
    nmb = nmb_at_thresholds(
        boot["mean_cost_diff"],
        boot["mean_qaly_diff"],
        thresholds=list(analysis.wtp_thresholds or []),
    )
    # CEAC grid: 0..max(thresholds*2, 50k) with 1k steps.
    wtps = list(analysis.wtp_thresholds or [30000])
    ceac_max = max(max(wtps) * 2, 50_000)
    ceac_curve = build_ceac(
        boot["plane_bootstrap"], wtp_range=(0, int(ceac_max), 1_000)
    )

    plane_png = render_ce_plane(
        boot["plane_bootstrap"],
        wtp_thresholds=wtps,
        intervention_label=analysis.intervention_label,
        comparator_label=analysis.comparator_label,
        currency=analysis.currency,
    )
    ceac_png = render_ceac(
        ceac_curve,
        wtp_thresholds=wtps,
        intervention_label=analysis.intervention_label,
        currency=analysis.currency,
    )

    res_repo = SqliteEconomicResultRepository(session)
    result = await res_repo.upsert(
        analysis_id=analysis_id,
        user_id=user_id,
        mean_cost_diff=float(boot["mean_cost_diff"]),
        mean_qaly_diff=float(boot["mean_qaly_diff"]),
        icer=icer_res["icer"],
        dominance_status=icer_res["dominance_status"],
        nmb_at_thresholds=nmb,
        ceac_data=ceac_curve,
        plane_bootstrap=boot["plane_bootstrap"],
        sensitivity=None,
        plane_png_uri=png_to_data_uri(plane_png),
        ceac_png_uri=png_to_data_uri(ceac_png),
    )
    fresh = await repo.get(analysis_id, user_id)
    return _hydrate(fresh, result)  # type: ignore[arg-type]


# ─── Sensitivity ───────────────────────────────────────────────────────────


@router.post(
    "/projects/{project_id}/economic-analyses/{analysis_id}/sensitivity",
    response_model=EconomicAnalysisRead,
)
async def run_sensitivity(
    project_id: str,
    analysis_id: str,
    body: SensitivityRequest,
    type: SensitivityKind = Query(...),  # noqa: A002 - matches spec
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> EconomicAnalysisRead:
    repo = SqliteEconomicAnalysisRepository(session)
    row = await repo.get(analysis_id, user_id)
    if row is None or row.project_id != project_id:
        raise HTTPException(status_code=404, detail="Economic analysis not found")
    res_repo = SqliteEconomicResultRepository(session)
    result = await res_repo.get_for_analysis(analysis_id, user_id)
    if result is None:
        raise HTTPException(
            status_code=422, detail="Run the analysis before sensitivity"
        )

    base_inputs = {
        "mean_cost_diff": float(result.mean_cost_diff),
        "mean_qaly_diff": float(result.mean_qaly_diff),
    }
    wtps = list(row.wtp_thresholds or [30000])
    wtp = float(max(wtps))
    try:
        if type == "psa":
            if not body.parameter_distributions:
                raise ValueError("parameter_distributions required for PSA")
            sens = psa(
                base_inputs,
                body.parameter_distributions,
                n_psa=body.n_psa,
                seed=body.seed,
                wtp=wtp,
            )
        elif type == "dsa":
            if not body.parameter_ranges:
                raise ValueError("parameter_ranges required for DSA")
            sens = dsa(base_inputs, body.parameter_ranges, wtp=wtp)
        elif type == "scenario":
            if not body.scenarios:
                raise ValueError("scenarios required for scenario analysis")
            sens = scenario(base_inputs, body.scenarios, wtp=wtp)
        else:  # pragma: no cover - guarded by Literal
            raise ValueError(f"unknown sensitivity type {type!r}")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None

    await res_repo.update_sensitivity(
        analysis_id=analysis_id, user_id=user_id, sensitivity=sens
    )
    fresh_result = await res_repo.get_for_analysis(analysis_id, user_id)
    return _hydrate(row, fresh_result)


# ─── Interpret ─────────────────────────────────────────────────────────────


@router.post(
    "/projects/{project_id}/economic-analyses/{analysis_id}/interpret",
    response_model=EconomicAnalysisRead,
)
async def interpret_economic(
    project_id: str,
    analysis_id: str,
    container: Container = Depends(get_container),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> EconomicAnalysisRead:
    repo = SqliteEconomicAnalysisRepository(session)
    row = await repo.get(analysis_id, user_id)
    if row is None or row.project_id != project_id:
        raise HTTPException(status_code=404, detail="Economic analysis not found")
    res_repo = SqliteEconomicResultRepository(session)
    result = await res_repo.get_for_analysis(analysis_id, user_id)
    if result is None:
        raise HTTPException(
            status_code=422, detail="Economic analysis has no result; run it first"
        )

    cite_token = (
        f"[CITE_dataset_{row.dataset_id}]" if row.dataset_id else "[CITE_dataset_]"
    )
    try:
        prose = await container.ai.interpret_economic_result(
            name=row.name,
            perspective=row.perspective,
            time_horizon_months=row.time_horizon_months,
            currency=row.currency,
            discount_rate_costs=row.discount_rate_costs,
            discount_rate_qalys=row.discount_rate_qalys,
            intervention_label=row.intervention_label,
            comparator_label=row.comparator_label,
            value_set=row.utility_value_set,
            mean_cost_diff=float(result.mean_cost_diff),
            mean_qaly_diff=float(result.mean_qaly_diff),
            icer=result.icer,
            dominance_status=result.dominance_status,
            nmb_at_thresholds=dict(result.nmb_at_thresholds or {}),
            ceac_data=list(result.ceac_data or []),
            wtp_thresholds=list(row.wtp_thresholds or []),
            sensitivity=dict(result.sensitivity or {}) if result.sensitivity else None,
            cite_token=cite_token,
        )
    except (AIProviderUnavailable, AIRateLimited, AISourceInsufficient, AIError) as exc:
        raise _map_ai_error(exc) from None
    except Exception:  # noqa: BLE001
        log.exception("Unexpected AI error in interpret_economic")
        raise HTTPException(status_code=503, detail="AI provider unavailable") from None

    await repo.update_interpretation(
        analysis_id=analysis_id, user_id=user_id, ai_interpretation=prose
    )
    fresh = await repo.get(analysis_id, user_id)
    return _hydrate(fresh, result)  # type: ignore[arg-type]


# ─── Push to manuscript ────────────────────────────────────────────────────


class _DatasetSyntheticArticle:
    def __init__(self, dataset) -> None:  # type: ignore[no-untyped-def]
        self.title = dataset.filename or "Dataset"
        self.authors = ["Project investigators"]
        year_val: int | None = None
        if getattr(dataset, "created_at", None) is not None:
            year_val = dataset.created_at.year
        self.year = year_val
        self.journal = None
        self.doi = None
        self.volume = None
        self.issue = None
        self.pages = None


@router.post(
    "/projects/{project_id}/economic-analyses/{analysis_id}/push",
    response_model=ManuscriptSectionRead,
)
async def push_economic_to_manuscript(
    project_id: str,
    analysis_id: str,
    body: PushEconomicRequest,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> ManuscriptSectionRead:
    repo = SqliteEconomicAnalysisRepository(session)
    row = await repo.get(analysis_id, user_id)
    if row is None or row.project_id != project_id:
        raise HTTPException(status_code=404, detail="Economic analysis not found")
    res_repo = SqliteEconomicResultRepository(session)
    result = await res_repo.get_for_analysis(analysis_id, user_id)
    if result is None or not row.ai_interpretation:
        raise HTTPException(
            status_code=422,
            detail="Economic analysis must be run and interpreted before pushing",
        )
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    ds_repo = SqliteDatasetRepository(session)
    dataset = None
    if row.dataset_id:
        dataset = await ds_repo.get(row.dataset_id, user_id)
    style: CitationStyle = (
        project.citation_style
        if project.citation_style in ("vancouver", "apa", "harvard", "ieee")
        else "vancouver"
    )  # type: ignore[assignment]
    articles_by_tag: dict[str, _DatasetSyntheticArticle] = {}
    if dataset is not None:
        articles_by_tag[f"dataset_{dataset.id}"] = _DatasetSyntheticArticle(dataset)
    resolved_prose = replace_cite_tokens_with_markup(
        row.ai_interpretation, articles_by_tag, style=style
    )

    # Compose a self-contained <figure class="economic-analysis"> block with
    # the plane PNG, the CEAC PNG, and the prose. Replace-by-class via
    # _push_to_section ensures re-pushes are idempotent.
    figure_html = (
        f'<figure class="economic-analysis">'
        f'<p>{resolved_prose}</p>'
        f'<img src="{result.plane_png_uri}" alt="Cost-effectiveness plane"/>'
        f'<img src="{result.ceac_png_uri}" alt="CEAC curve"/>'
        f'<figcaption>Cost-effectiveness plane and acceptability curve for '
        f'{row.intervention_label} vs {row.comparator_label} '
        f'(ICER {row.currency} {result.icer or 0:,.0f}/QALY; '
        f'dominance: {result.dominance_status}).</figcaption>'
        f'</figure>'
    )
    updated = await _push_to_section(
        session,
        project_id=project_id,
        section_name=body.section,
        html=figure_html,
        class_hook="economic-analysis",
        user_id=user_id,
    )
    return updated


# ─── CHEERS report ─────────────────────────────────────────────────────────


@router.get(
    "/projects/{project_id}/economic-analyses/{analysis_id}/cheers-report",
)
async def cheers_report(
    project_id: str,
    analysis_id: str,
    format: str = Query("docx", pattern="^(docx|pdf)$"),  # noqa: A002
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> Response:
    repo = SqliteEconomicAnalysisRepository(session)
    row = await repo.get(analysis_id, user_id)
    if row is None or row.project_id != project_id:
        raise HTTPException(status_code=404, detail="Economic analysis not found")
    res_repo = SqliteEconomicResultRepository(session)
    result = await res_repo.get_for_analysis(analysis_id, user_id)
    if result is None:
        raise HTTPException(
            status_code=422, detail="Run the analysis before exporting the CHEERS report"
        )
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    ctx = CHEERSContext(
        name=row.name,
        perspective=row.perspective,
        time_horizon_months=row.time_horizon_months,
        currency=row.currency,
        discount_rate_costs=row.discount_rate_costs,
        discount_rate_qalys=row.discount_rate_qalys,
        intervention_label=row.intervention_label,
        comparator_label=row.comparator_label,
        value_set=row.utility_value_set,
        bootstrap_n=row.bootstrap_n,
        seed=row.seed,
        mean_cost_diff=float(result.mean_cost_diff),
        mean_qaly_diff=float(result.mean_qaly_diff),
        icer=result.icer,
        dominance_status=result.dominance_status,
        nmb_at_thresholds=dict(result.nmb_at_thresholds or {}),
        wtp_thresholds=list(row.wtp_thresholds or []),
        ai_interpretation=row.ai_interpretation,
        plane_png_uri=result.plane_png_uri,
        ceac_png_uri=result.ceac_png_uri,
        sensitivity=dict(result.sensitivity or {}) if result.sensitivity else None,
    )
    body = build_economic_report(project, ctx, fmt=format)
    media = (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if format == "docx"
        else "application/pdf"
    )
    filename = f"cheers-report-{row.id}.{format}"
    return StreamingResponse(
        io.BytesIO(body),
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


__all__ = ["router"]
