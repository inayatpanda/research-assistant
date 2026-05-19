"""Analyses routes: recommend + create + run + interpret + push to manuscript."""
from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..container import Container, get_container
from ..db.models import Analysis, AnalysisResult, Dataset
from ..repositories.analyses import SqliteAnalysisRepository
from ..repositories.datasets import SqliteDatasetRepository
from ..repositories.manuscript_sections import SqliteManuscriptSectionRepository
from ..repositories.projects import SqliteProjectRepository
from ..schemas.analysis import (
    AnalysisCreate,
    AnalysisRead,
    AnalysisResultRead,
    InterpretResponse,
    PushToManuscriptRequest,
    RecommendRequest,
    RecommendResponse,
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
from ..services.stats import assumptions as assumptions_svc
from ..services.stats.ingest import read_table
from ..services.stats.registry import CATALOGUE, recommend
from ..services.stats.runner import run as runner_run

router = APIRouter(tags=["analyses"])
log = logging.getLogger("research_api.analyses")


async def _session(
    container: Container = Depends(get_container),
) -> AsyncIterator[AsyncSession]:
    async with container.session_factory() as s:
        yield s


def _user_id(container: Container = Depends(get_container)) -> str:
    return container.settings.local_user_id


def _column_type_map(variables: list) -> dict[str, str]:
    out: dict[str, str] = {}
    for v in variables:
        out[v.name] = v.user_type or v.inferred_type
    return out


def _validate_columns(variables: list, var_spec: dict[str, Any]) -> None:
    allowed = {v.name for v in variables}
    for v in var_spec.values():
        if isinstance(v, str):
            if v not in allowed:
                raise HTTPException(
                    status_code=422,
                    detail=f"variable {v!r} is not in dataset columns",
                )
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, str) and item not in allowed:
                    raise HTTPException(
                        status_code=422,
                        detail=f"variable {item!r} is not in dataset columns",
                    )


def _to_var_types(
    variables: list, var_names: dict[str, str | list[str]]
) -> dict[str, Any]:
    types = _column_type_map(variables)
    out: dict[str, Any] = {}
    for key, val in var_names.items():
        if isinstance(val, str):
            out[key] = types.get(val)
        elif isinstance(val, list):
            out[key] = [types.get(v) for v in val if isinstance(v, str)]
    return out


def _hydrate_analysis(
    analysis: Analysis, result: AnalysisResult | None
) -> AnalysisRead:
    read = AnalysisRead.model_validate(analysis)
    if result is not None:
        read.result = AnalysisResultRead.model_validate(result)
    return read


def _map_ai_error(e: Exception) -> HTTPException:
    log.warning("AI error: %s: %s", type(e).__name__, e)
    if isinstance(e, AIRateLimited):
        return HTTPException(status_code=429, detail="AI rate limited")
    if isinstance(e, AISourceInsufficient):
        return HTTPException(
            status_code=422, detail="insufficient input to interpret result"
        )
    return HTTPException(status_code=503, detail="AI provider unavailable")


async def _load_dataframe(
    container: Container, dataset: Dataset
) -> pd.DataFrame:
    from ..services.storage import StorageRef
    from ..services.stats.ingest import read_dataset

    ref = StorageRef(backend=dataset.file_ref["backend"], key=dataset.file_ref["key"])
    data = await container.storage.read(ref)
    return read_dataset(data, dataset)


async def _load_dataframe_with_transformations(
    container: Container,
    dataset: Dataset,
    session: AsyncSession,
    user_id: str,
) -> pd.DataFrame:
    """Phase 13 (MP13) — Load the raw CSV, then replay any transformations.

    The runner sees the post-transformation DataFrame. If the dataset has
    no transformations, behaves identically to ``_load_dataframe``.
    """
    from ..repositories.transformations import SqliteTransformationRepository
    from ..services.stats.transform import apply_transformations

    df = await _load_dataframe(container, dataset)
    trepo = SqliteTransformationRepository(session)
    transformations = await trepo.list_for_dataset(dataset.id, user_id)
    if not transformations:
        return df
    ops = [
        {"op_type": t.op_type, "op_args": t.op_args}
        for t in transformations  # already sorted by position asc
    ]
    return apply_transformations(df, ops)


def _maybe_normality_warning(
    df: pd.DataFrame, var_spec: dict[str, Any]
) -> list[str]:
    warnings: list[str] = []
    outcome = var_spec.get("outcome")
    groups = var_spec.get("groups")
    if isinstance(outcome, str) and outcome in df.columns:
        if isinstance(groups, str) and groups in df.columns:
            for lv, sub in df.groupby(groups):
                values = sub[outcome].dropna().to_numpy(dtype="float", copy=False)
                if values.size < 3:
                    continue
                check = assumptions_svc.shapiro(values.tolist())
                if not check.ok:
                    warnings.append(
                        f"Normality may not hold in group {lv!r} (Shapiro p={check.p_value:.4f})."
                    )
        else:
            values = df[outcome].dropna().to_numpy(dtype="float", copy=False)
            if values.size >= 3:
                check = assumptions_svc.shapiro(values.tolist())
                if not check.ok:
                    warnings.append(
                        f"Normality may not hold for {outcome!r} (Shapiro p={check.p_value:.4f})."
                    )
    return warnings


def _compute_assumptions(
    df: pd.DataFrame, var_spec: dict[str, Any], test_key: str
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    outcome = var_spec.get("outcome")
    groups = var_spec.get("groups")
    if test_key in {
        "independent_t",
        "paired_t",
        "mann_whitney",
        "wilcoxon_signed",
        "one_way_anova",
        "kruskal_wallis",
        "pearson",
        "spearman",
    }:
        x = var_spec.get("x") if "x" in var_spec else outcome
        if isinstance(x, str) and x in df.columns:
            values = df[x].dropna().to_numpy(dtype="float", copy=False)
            if values.size >= 3:
                sw = assumptions_svc.shapiro(values.tolist())
                out["shapiro"] = {
                    "statistic": sw.statistic,
                    "p_value": sw.p_value,
                    "ok": sw.ok,
                }
    if (
        isinstance(outcome, str)
        and isinstance(groups, str)
        and outcome in df.columns
        and groups in df.columns
    ):
        try:
            arrs: list[list[float]] = []
            for _, sub in df.groupby(groups):
                arr = sub[outcome].dropna().tolist()
                if len(arr) >= 2:
                    arrs.append(arr)
            if len(arrs) >= 2:
                lev = assumptions_svc.levene(*arrs)
                out["levene"] = {
                    "statistic": lev.statistic,
                    "p_value": lev.p_value,
                    "ok": lev.ok,
                }
        except Exception:  # noqa: BLE001
            pass
    if test_key == "cox_ph":
        time_col = var_spec.get("time")
        event_col = var_spec.get("event")
        covariates = var_spec.get("covariates")
        if (
            isinstance(time_col, str)
            and isinstance(event_col, str)
            and covariates
        ):
            try:
                cov_list = (
                    [covariates] if isinstance(covariates, str) else list(covariates)
                )
                ph = assumptions_svc.proportional_hazards_check(
                    df, duration_col=time_col, event_col=event_col, covariate_cols=cov_list
                )
                out["prop_hazards"] = {
                    "statistic": ph.statistic,
                    "p_value": ph.p_value,
                    "ok": ph.ok,
                }
            except Exception:  # noqa: BLE001
                pass
    return out


@router.post(
    "/projects/{project_id}/datasets/{dataset_id}/analyses/recommend",
    response_model=RecommendResponse,
)
async def recommend_test(
    project_id: str,
    dataset_id: str,
    body: RecommendRequest,
    container: Container = Depends(get_container),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> RecommendResponse:
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    ds_repo = SqliteDatasetRepository(session)
    dataset = await ds_repo.get(dataset_id, user_id)
    if dataset is None or dataset.project_id != project_id:
        raise HTTPException(status_code=404, detail="Dataset not found")
    variables = await ds_repo.list_variables(dataset_id, user_id)
    _validate_columns(variables, body.variables)

    var_types = _to_var_types(variables, body.variables)
    # Try to derive n_groups from data when possible
    n_groups: int | None = None
    paired = False
    groups_col = body.variables.get("groups")
    normality_ok: bool | None = None
    try:
        if isinstance(groups_col, str):
            df = await _load_dataframe(container, dataset)
            n_groups = int(df[groups_col].dropna().nunique())
            normality_warnings = _maybe_normality_warning(df, dict(body.variables))
            normality_ok = len(normality_warnings) == 0
        else:
            normality_warnings = []
    except Exception:  # noqa: BLE001
        normality_warnings = []

    try:
        test_key, rationale = recommend(
            question_type=body.question_type,
            var_types=var_types,
            n_groups=n_groups,
            paired=paired,
            normality_ok=normality_ok,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return RecommendResponse(
        chosen_test=test_key,
        rationale=rationale,
        assumption_warnings=normality_warnings,
    )


@router.post(
    "/projects/{project_id}/datasets/{dataset_id}/analyses",
    response_model=AnalysisRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_analysis(
    project_id: str,
    dataset_id: str,
    body: AnalysisCreate,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> AnalysisRead:
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    ds_repo = SqliteDatasetRepository(session)
    dataset = await ds_repo.get(dataset_id, user_id)
    if dataset is None or dataset.project_id != project_id:
        raise HTTPException(status_code=404, detail="Dataset not found")

    variables = await ds_repo.list_variables(dataset_id, user_id)
    _validate_columns(variables, body.variables)

    spec = CATALOGUE.get(body.chosen_test)
    if spec is None:
        raise HTTPException(status_code=422, detail="Unknown test_key")

    repo = SqliteAnalysisRepository(session)
    analysis = await repo.create(
        project_id=project_id,
        dataset_id=dataset_id,
        question_type=body.question_type,
        chosen_test=body.chosen_test,
        recommendation_rationale=spec.rationale,
        variables=body.variables,
        status="ready",
        user_id=user_id,
    )
    return _hydrate_analysis(analysis, None)


@router.get(
    "/projects/{project_id}/datasets/{dataset_id}/analyses",
    response_model=list[AnalysisRead],
)
async def list_analyses(
    project_id: str,
    dataset_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> list[AnalysisRead]:
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    ds_repo = SqliteDatasetRepository(session)
    dataset = await ds_repo.get(dataset_id, user_id)
    if dataset is None or dataset.project_id != project_id:
        raise HTTPException(status_code=404, detail="Dataset not found")

    repo = SqliteAnalysisRepository(session)
    analyses = await repo.list_for_dataset(
        project_id=project_id, dataset_id=dataset_id, user_id=user_id
    )
    out: list[AnalysisRead] = []
    for a in analyses:
        result = await repo.get_result(a.id, user_id)
        out.append(_hydrate_analysis(a, result))
    return out


@router.get(
    "/projects/{project_id}/analyses/{analysis_id}",
    response_model=AnalysisRead,
)
async def get_analysis(
    project_id: str,
    analysis_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> AnalysisRead:
    repo = SqliteAnalysisRepository(session)
    analysis = await repo.get(analysis_id, user_id)
    if analysis is None or analysis.project_id != project_id:
        raise HTTPException(status_code=404, detail="Analysis not found")
    result = await repo.get_result(analysis_id, user_id)
    return _hydrate_analysis(analysis, result)


@router.delete(
    "/projects/{project_id}/analyses/{analysis_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_analysis(
    project_id: str,
    analysis_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> None:
    repo = SqliteAnalysisRepository(session)
    analysis = await repo.get(analysis_id, user_id)
    if analysis is None or analysis.project_id != project_id:
        raise HTTPException(status_code=404, detail="Analysis not found")
    await repo.delete(analysis_id, user_id)
    return None


@router.post(
    "/projects/{project_id}/analyses/{analysis_id}/run",
    response_model=AnalysisRead,
)
async def run_analysis(
    project_id: str,
    analysis_id: str,
    container: Container = Depends(get_container),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> AnalysisRead:
    repo = SqliteAnalysisRepository(session)
    pair = await repo.get_with_dataset(analysis_id, user_id)
    if pair is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    analysis, dataset = pair
    if analysis.project_id != project_id:
        raise HTTPException(status_code=404, detail="Analysis not found")

    ds_repo = SqliteDatasetRepository(session)
    variables = await ds_repo.list_variables(dataset.id, user_id)
    _validate_columns(variables, analysis.variables)

    try:
        df = await _load_dataframe_with_transformations(
            container, dataset, session, user_id
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("Failed to load dataset bytes: %s", exc)
        raise HTTPException(status_code=422, detail="Could not load dataset") from None

    try:
        await repo.update_status(analysis_id, "running", user_id)
        result_obj = runner_run(
            test_key=analysis.chosen_test, df=df, variables=dict(analysis.variables)
        )
    except ValueError as exc:
        await repo.update_status(analysis_id, "failed", user_id)
        raise HTTPException(status_code=422, detail=str(exc)) from None
    except Exception as exc:  # noqa: BLE001
        log.warning("Analysis run failed: %s", exc)
        await repo.update_status(analysis_id, "failed", user_id)
        raise HTTPException(
            status_code=422, detail=f"Analysis run failed: {exc}"
        ) from None

    summary = {
        "statistic": result_obj.statistic,
        "p_value": result_obj.p_value,
        "effect_size": result_obj.effect_size,
        "ci_low": result_obj.ci_low,
        "ci_high": result_obj.ci_high,
        "n": result_obj.n,
        "df": result_obj.df,
        "extras": result_obj.extras,
    }
    assumptions = _compute_assumptions(df, dict(analysis.variables), analysis.chosen_test)
    await repo.update_result(
        analysis_id=analysis_id,
        summary=summary,
        assumptions=assumptions,
        chart=result_obj.chart,
        user_id=user_id,
    )
    await repo.update_status(analysis_id, "completed", user_id)
    fresh = await repo.get(analysis_id, user_id)
    result = await repo.get_result(analysis_id, user_id)
    return _hydrate_analysis(fresh, result)  # type: ignore[arg-type]


@router.post(
    "/projects/{project_id}/analyses/{analysis_id}/interpret",
    response_model=AnalysisRead,
)
async def interpret_analysis(
    project_id: str,
    analysis_id: str,
    container: Container = Depends(get_container),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> AnalysisRead:
    repo = SqliteAnalysisRepository(session)
    analysis = await repo.get(analysis_id, user_id)
    if analysis is None or analysis.project_id != project_id:
        raise HTTPException(status_code=404, detail="Analysis not found")
    result = await repo.get_result(analysis_id, user_id)
    if result is None:
        raise HTTPException(
            status_code=422, detail="Analysis has no result; run it first"
        )

    spec = CATALOGUE.get(analysis.chosen_test)
    test_label = spec.label if spec else analysis.chosen_test
    cite_token = f"[CITE_dataset_{analysis.dataset_id}]"
    try:
        prose = await container.ai.interpret_result(
            test_label=test_label,
            rationale=analysis.recommendation_rationale,
            summary=dict(result.summary),
            assumptions=dict(result.assumptions) if result.assumptions else None,
            cite_token=cite_token,
        )
    except (AIProviderUnavailable, AIRateLimited, AISourceInsufficient, AIError) as exc:
        raise _map_ai_error(exc) from None
    except Exception:
        log.exception("Unexpected AI error in interpret_analysis")
        raise HTTPException(status_code=503, detail="AI provider unavailable") from None

    await repo.update_interpretation(
        analysis_id=analysis_id, ai_interpretation=prose, user_id=user_id
    )
    fresh_result = await repo.get_result(analysis_id, user_id)
    return _hydrate_analysis(analysis, fresh_result)


class _DatasetSyntheticArticle:
    """Article-like adapter so a Dataset can be cited via the standard
    `[CITE_dataset_<id>]` pipeline.  The bibliography panel resolves
    `data-article-id="dataset_<id>"` against this same shape via the
    project's articles repository when the dataset id is registered.
    """

    def __init__(self, dataset) -> None:  # type: ignore[no-untyped-def]
        self.title = dataset.filename or "Dataset"
        # Synthetic single-author so author/year inline formatters render
        # `Dataset, <year>` rather than `Unknown source`.
        self.authors = ["Dataset"]
        # `created_at` is timezone-aware; fall back to None if unset.
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
    "/projects/{project_id}/analyses/{analysis_id}/push",
    response_model=ManuscriptSectionRead,
)
async def push_to_manuscript(
    project_id: str,
    analysis_id: str,
    body: PushToManuscriptRequest,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> ManuscriptSectionRead:
    repo = SqliteAnalysisRepository(session)
    analysis = await repo.get(analysis_id, user_id)
    if analysis is None or analysis.project_id != project_id:
        raise HTTPException(status_code=404, detail="Analysis not found")
    result = await repo.get_result(analysis_id, user_id)
    if result is None or not result.ai_interpretation:
        raise HTTPException(
            status_code=422,
            detail="Analysis must be interpreted before pushing to manuscript",
        )
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    # Resolve the dataset CITE token (and any other tokens the AI emitted)
    # before persisting so the manuscript never carries raw `[CITE_xxx]`.
    ds_repo = SqliteDatasetRepository(session)
    dataset = await ds_repo.get(analysis.dataset_id, user_id)
    style: CitationStyle = (
        project.citation_style if project.citation_style in ("vancouver", "apa", "harvard", "ieee")
        else "vancouver"
    )  # type: ignore[assignment]
    articles_by_tag: dict[str, _DatasetSyntheticArticle] = {}
    if dataset is not None:
        articles_by_tag[f"dataset_{dataset.id}"] = _DatasetSyntheticArticle(dataset)
    resolved = replace_cite_tokens_with_markup(
        result.ai_interpretation,
        articles_by_tag,
        style=style,
    )

    section_name = "Results"
    sec_repo = SqliteManuscriptSectionRepository(session)
    existing = await sec_repo.get(
        project_id=project_id, section_name=section_name, user_id=user_id
    )
    paragraph = f"<p>{resolved}</p>"
    new_content = paragraph if existing is None or not existing.content else (
        existing.content + paragraph
    )
    updated = await sec_repo.upsert(
        project_id=project_id,
        section_name=section_name,
        content=new_content,
        user_id=user_id,
    )
    return ManuscriptSectionRead.model_validate(updated)
