"""Meta-analysis routes: CRUD + run + plots + interpret + push."""
from __future__ import annotations

import base64
import logging
from collections.abc import AsyncIterator
from html import escape

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..container import Container, get_container
from ..repositories.articles import SqliteArticleRepository
from ..repositories.meta import MetaArticleMismatch, SqliteMetaRepository
from ..repositories.projects import SqliteProjectRepository
from ..repositories.reviews import SqliteReviewRepository
from ..schemas.manuscript_section import ManuscriptSectionRead
from ..schemas.meta import (
    MetaAnalysisCreate,
    MetaAnalysisRead,
    MetaAnalysisUpdate,
    MetaInputCreate,
    MetaInputRead,
    MetaInputUpdate,
)
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
from ..services.export.bibliography import collect_used_article_ids_in_order
from ..repositories.manuscript_sections import SqliteManuscriptSectionRepository
from ..services.meta import effect_sizes as es
from ..services.meta.forest_plot import ForestRow, render_forest_png
from ..services.meta.funnel_plot import render_funnel_png
from ..services.meta.heterogeneity import Heterogeneity, heterogeneity as compute_het
from ..services.meta.pooling import PooledResult, pool
from .reviews import _push_to_section

router = APIRouter(tags=["meta-analysis"])
log = logging.getLogger("research_api.reviews_meta")


_METRIC_LABELS: dict[str, str] = {
    "md": "Mean difference",
    "smd": "Standardised mean difference",
    "or": "Odds ratio",
    "rr": "Risk ratio",
    "hr": "Hazard ratio",
    "r": "Correlation",
}

_LOG_SCALE_METRICS = {"or", "rr", "hr"}


async def _session(
    container: Container = Depends(get_container),
) -> AsyncIterator[AsyncSession]:
    async with container.session_factory() as s:
        yield s


def _user_id(container: Container = Depends(get_container)) -> str:
    return container.settings.local_user_id


async def _resolve_review(project_id: str, session: AsyncSession, user_id: str):
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    repo = SqliteReviewRepository(session)
    review = await repo.get_or_create(project_id=project_id, user_id=user_id)
    return repo, review


def _hydrate_meta(meta, inputs) -> MetaAnalysisRead:
    read = MetaAnalysisRead.model_validate(meta)
    read.inputs = [MetaInputRead.model_validate(i) for i in inputs]
    return read


def _map_ai_error(e: Exception) -> HTTPException:
    log.warning("AI error: %s: %s", type(e).__name__, e)
    if isinstance(e, AIRateLimited):
        return HTTPException(status_code=429, detail="AI rate limited")
    if isinstance(e, AISourceInsufficient):
        return HTTPException(status_code=422, detail="insufficient input to interpret meta-analysis")
    return HTTPException(status_code=503, detail="AI provider unavailable")


def _input_to_effect(metric: str, inp) -> es.Effect:
    """Convert a MetaInput model into an Effect on the analysis scale."""
    if metric == "md":
        if None in (inp.mean_a, inp.sd_a, inp.n_a, inp.mean_b, inp.sd_b, inp.n_b):
            raise ValueError("MD requires mean_a, sd_a, n_a, mean_b, sd_b, n_b")
        return es.md(
            mean_a=inp.mean_a, sd_a=inp.sd_a, n_a=inp.n_a,
            mean_b=inp.mean_b, sd_b=inp.sd_b, n_b=inp.n_b,
        )
    if metric == "smd":
        if None in (inp.mean_a, inp.sd_a, inp.n_a, inp.mean_b, inp.sd_b, inp.n_b):
            raise ValueError("SMD requires mean_a, sd_a, n_a, mean_b, sd_b, n_b")
        return es.smd_hedges_g(
            mean_a=inp.mean_a, sd_a=inp.sd_a, n_a=inp.n_a,
            mean_b=inp.mean_b, sd_b=inp.sd_b, n_b=inp.n_b,
        )
    if metric == "or":
        if None in (inp.events_a, inp.n_a_total, inp.events_b, inp.n_b_total):
            raise ValueError("OR requires events_a, n_a_total, events_b, n_b_total")
        return es.odds_ratio(
            events_a=inp.events_a, n_a=inp.n_a_total,
            events_b=inp.events_b, n_b=inp.n_b_total,
        )
    if metric == "rr":
        if None in (inp.events_a, inp.n_a_total, inp.events_b, inp.n_b_total):
            raise ValueError("RR requires events_a, n_a_total, events_b, n_b_total")
        return es.risk_ratio(
            events_a=inp.events_a, n_a=inp.n_a_total,
            events_b=inp.events_b, n_b=inp.n_b_total,
        )
    if metric == "hr":
        if inp.log_hr is not None and inp.se_log_hr is not None:
            return es.hazard_ratio_from_logs(log_hr=inp.log_hr, se_log_hr=inp.se_log_hr)
        if None not in (inp.hr, inp.hr_ci_low, inp.hr_ci_high):
            return es.hazard_ratio_from_ci(
                hr=inp.hr, hr_ci_low=inp.hr_ci_low, hr_ci_high=inp.hr_ci_high
            )
        raise ValueError("HR requires (log_hr, se_log_hr) or (hr, hr_ci_low, hr_ci_high)")
    if metric == "r":
        if None in (inp.r, inp.n_r):
            raise ValueError("r requires r and n_r")
        return es.correlation_fisher_z(r=inp.r, n=inp.n_r)
    raise ValueError(f"unsupported metric: {metric!r}")


def _resolve_subgroup(extraction_fields: dict | None, dotted_path: str) -> str | None:
    if extraction_fields is None:
        return None
    parts = dotted_path.split(".")
    cur = extraction_fields
    for p in parts:
        if not isinstance(cur, dict) or p not in cur:
            return None
        cur = cur[p]
    if cur is None or cur == "":
        return None
    return str(cur)


# ── CRUD ────────────────────────────────────────────────────────────────


@router.get(
    "/projects/{project_id}/reviews/meta",
    response_model=list[MetaAnalysisRead],
)
async def list_meta_analyses(
    project_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> list[MetaAnalysisRead]:
    _, review = await _resolve_review(project_id, session, user_id)
    repo = SqliteMetaRepository(session)
    rows = await repo.list(review_id=review.id, user_id=user_id)
    out: list[MetaAnalysisRead] = []
    for meta in rows:
        inputs = await repo.list_inputs(meta.id, user_id)
        out.append(_hydrate_meta(meta, inputs))
    return out


@router.post(
    "/projects/{project_id}/reviews/meta",
    response_model=MetaAnalysisRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_meta_analysis(
    project_id: str,
    body: MetaAnalysisCreate,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> MetaAnalysisRead:
    _, review = await _resolve_review(project_id, session, user_id)
    if len(body.inputs) < 2:
        raise HTTPException(status_code=422, detail="Meta-analysis requires at least 2 studies")
    repo = SqliteMetaRepository(session)
    try:
        meta = await repo.create(review_id=review.id, data=body, user_id=user_id)
    except MetaArticleMismatch as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    inputs = await repo.list_inputs(meta.id, user_id)
    return _hydrate_meta(meta, inputs)


@router.get(
    "/projects/{project_id}/reviews/meta/{meta_id}",
    response_model=MetaAnalysisRead,
)
async def get_meta_analysis(
    project_id: str,
    meta_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> MetaAnalysisRead:
    _, review = await _resolve_review(project_id, session, user_id)
    repo = SqliteMetaRepository(session)
    pair = await repo.get_with_inputs(meta_id, user_id)
    if pair is None or pair[0].review_id != review.id:
        raise HTTPException(status_code=404, detail="Meta-analysis not found")
    meta, inputs = pair
    return _hydrate_meta(meta, inputs)


@router.patch(
    "/projects/{project_id}/reviews/meta/{meta_id}",
    response_model=MetaAnalysisRead,
)
async def update_meta_analysis(
    project_id: str,
    meta_id: str,
    body: MetaAnalysisUpdate,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> MetaAnalysisRead:
    _, review = await _resolve_review(project_id, session, user_id)
    repo = SqliteMetaRepository(session)
    existing = await repo.get(meta_id, user_id)
    if existing is None or existing.review_id != review.id:
        raise HTTPException(status_code=404, detail="Meta-analysis not found")
    updated = await repo.update(meta_id, body, user_id)
    if updated is None:
        raise HTTPException(status_code=404, detail="Meta-analysis not found")
    inputs = await repo.list_inputs(meta_id, user_id)
    return _hydrate_meta(updated, inputs)


@router.delete(
    "/projects/{project_id}/reviews/meta/{meta_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_meta_analysis(
    project_id: str,
    meta_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> None:
    _, review = await _resolve_review(project_id, session, user_id)
    repo = SqliteMetaRepository(session)
    existing = await repo.get(meta_id, user_id)
    if existing is None or existing.review_id != review.id:
        raise HTTPException(status_code=404, detail="Meta-analysis not found")
    await repo.delete(meta_id, user_id)
    return None


@router.post(
    "/projects/{project_id}/reviews/meta/{meta_id}/inputs",
    response_model=MetaInputRead,
    status_code=status.HTTP_201_CREATED,
)
async def upsert_meta_input(
    project_id: str,
    meta_id: str,
    body: MetaInputCreate,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> MetaInputRead:
    _, review = await _resolve_review(project_id, session, user_id)
    repo = SqliteMetaRepository(session)
    existing = await repo.get(meta_id, user_id)
    if existing is None or existing.review_id != review.id:
        raise HTTPException(status_code=404, detail="Meta-analysis not found")
    try:
        row = await repo.upsert_input(meta_id=meta_id, data=body, user_id=user_id)
    except MetaArticleMismatch as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return MetaInputRead.model_validate(row)


@router.patch(
    "/projects/{project_id}/reviews/meta/{meta_id}/inputs/{input_id}",
    response_model=MetaInputRead,
)
async def update_meta_input(
    project_id: str,
    meta_id: str,
    input_id: str,
    body: MetaInputUpdate,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> MetaInputRead:
    _, review = await _resolve_review(project_id, session, user_id)
    repo = SqliteMetaRepository(session)
    existing = await repo.get(meta_id, user_id)
    if existing is None or existing.review_id != review.id:
        raise HTTPException(status_code=404, detail="Meta-analysis not found")
    updated = await repo.update_input(input_id, body, user_id)
    if updated is None or updated.meta_id != meta_id:
        raise HTTPException(status_code=404, detail="Input not found")
    return MetaInputRead.model_validate(updated)


@router.delete(
    "/projects/{project_id}/reviews/meta/{meta_id}/inputs/{input_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_meta_input(
    project_id: str,
    meta_id: str,
    input_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> None:
    _, review = await _resolve_review(project_id, session, user_id)
    repo = SqliteMetaRepository(session)
    existing = await repo.get(meta_id, user_id)
    if existing is None or existing.review_id != review.id:
        raise HTTPException(status_code=404, detail="Meta-analysis not found")
    # Confirm input belongs to this meta
    inputs = await repo.list_inputs(meta_id, user_id)
    if not any(inp.id == input_id for inp in inputs):
        raise HTTPException(status_code=404, detail="Input not found")
    await repo.delete_input(input_id, user_id)
    return None


# ── Run ────────────────────────────────────────────────────────────────


@router.post(
    "/projects/{project_id}/reviews/meta/{meta_id}/run",
    response_model=MetaAnalysisRead,
)
async def run_meta_analysis(
    project_id: str,
    meta_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> MetaAnalysisRead:
    repo_review, review = await _resolve_review(project_id, session, user_id)
    repo = SqliteMetaRepository(session)
    pair = await repo.get_with_inputs(meta_id, user_id)
    if pair is None or pair[0].review_id != review.id:
        raise HTTPException(status_code=404, detail="Meta-analysis not found")
    meta, inputs = pair
    if len(inputs) < 2:
        raise HTTPException(status_code=422, detail="Meta-analysis requires at least 2 inputs")

    await repo.set_status(meta_id=meta_id, user_id=user_id, status="running")

    # Build effects + resolve subgroup if requested
    try:
        effects: list[es.Effect] = []
        subgroup_by_input_id: dict[str, str | None] = {}
        if meta.subgroup_variable:
            extractions = {
                ext.article_id: ext for ext in await repo_review.list_extraction(review.id, user_id)
            }
        else:
            extractions = {}
        for inp in inputs:
            try:
                eff = _input_to_effect(meta.effect_metric, inp)
            except ValueError as exc:
                await repo.set_status(meta_id=meta_id, user_id=user_id, status="failed")
                raise HTTPException(
                    status_code=422,
                    detail=f"Study {inp.id} has invalid inputs for metric {meta.effect_metric}: {exc}",
                ) from None
            effects.append(eff)
            # Subgroup resolution
            if meta.subgroup_variable:
                ext = extractions.get(inp.article_id)
                fields = ext.fields if ext else None
                sg = _resolve_subgroup(fields, meta.subgroup_variable) or "Unspecified"
                subgroup_by_input_id[inp.id] = sg
                await repo.set_input_subgroup(input_id=inp.id, user_id=user_id, subgroup=sg)
            else:
                subgroup_by_input_id[inp.id] = None

        het = compute_het(effects)
        pooled = pool(effects, meta.model)
    except HTTPException:
        raise
    except ValueError as exc:
        await repo.set_status(meta_id=meta_id, user_id=user_id, status="failed")
        raise HTTPException(status_code=422, detail=str(exc)) from None
    except Exception:
        log.exception("Unexpected error in run_meta_analysis")
        await repo.set_status(meta_id=meta_id, user_id=user_id, status="failed")
        raise HTTPException(status_code=500, detail="Failed to run meta-analysis") from None

    # Subgroup pooled summaries
    subgroup_summary: dict | None = None
    if meta.subgroup_variable:
        subgroup_summary = {}
        # Group by subgroup
        per_sg: dict[str, list[tuple[es.Effect, str]]] = {}
        for inp, eff in zip(inputs, effects):
            sg = subgroup_by_input_id.get(inp.id) or "Unspecified"
            per_sg.setdefault(sg, []).append((eff, inp.id))
        for sg, items in per_sg.items():
            eff_list = [e for e, _ in items]
            k = len(eff_list)
            entry: dict[str, float | int | None] = {
                "k": k,
                "estimate": None,
                "ci_low": None,
                "ci_high": None,
                "i2": None,
            }
            if k >= 2:
                try:
                    sg_pooled = pool(eff_list, meta.model)
                    sg_het = compute_het(eff_list)
                    entry["estimate"] = sg_pooled.estimate
                    entry["ci_low"] = sg_pooled.ci_low
                    entry["ci_high"] = sg_pooled.ci_high
                    entry["i2"] = sg_het.i2
                except Exception:  # noqa: BLE001
                    log.exception("subgroup pool failed for %s", sg)
            subgroup_summary[sg] = entry

    await repo.write_pooled(
        meta_id=meta_id, user_id=user_id,
        pooled=pooled, heterogeneity=het, subgroup_summary=subgroup_summary,
    )

    fresh = await repo.get(meta_id, user_id)
    fresh_inputs = await repo.list_inputs(meta_id, user_id)
    return _hydrate_meta(fresh, fresh_inputs)


# ── Plots ──────────────────────────────────────────────────────────────


async def _load_meta_for_plot(
    project_id: str, meta_id: str, session: AsyncSession, user_id: str
):
    _, review = await _resolve_review(project_id, session, user_id)
    repo = SqliteMetaRepository(session)
    pair = await repo.get_with_inputs(meta_id, user_id)
    if pair is None or pair[0].review_id != review.id:
        raise HTTPException(status_code=404, detail="Meta-analysis not found")
    meta, inputs = pair
    if meta.status != "completed":
        raise HTTPException(status_code=409, detail="Run the analysis first")
    return meta, inputs


def _build_forest_rows_and_pooled(meta, inputs):
    effects = [_input_to_effect(meta.effect_metric, inp) for inp in inputs]
    pooled = pool(effects, meta.model)
    rows: list[ForestRow] = []
    for inp, eff, w in zip(inputs, effects, pooled.weights):
        label = inp.study_label or inp.article_id
        rows.append(ForestRow(
            label=label,
            yi=eff.yi,
            ci_low=eff.yi - 1.959964 * eff.se,
            ci_high=eff.yi + 1.959964 * eff.se,
            weight_pct=100.0 * w,
            subgroup=inp.subgroup,
        ))
    return rows, pooled, effects


@router.get("/projects/{project_id}/reviews/meta/{meta_id}/forest.png")
async def get_forest_png(
    project_id: str,
    meta_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> Response:
    meta, inputs = await _load_meta_for_plot(project_id, meta_id, session, user_id)
    rows, pooled, _effects = _build_forest_rows_and_pooled(meta, inputs)
    metric_label = _METRIC_LABELS.get(meta.effect_metric, meta.effect_metric)
    log_scale = meta.effect_metric in _LOG_SCALE_METRICS

    subgroup_summaries: dict[str, tuple[float, float, float]] | None = None
    if meta.subgroup_summary:
        subgroup_summaries = {}
        for sg, payload in meta.subgroup_summary.items():
            if payload.get("estimate") is None:
                continue
            subgroup_summaries[sg] = (
                payload["estimate"],
                payload["ci_low"],
                payload["ci_high"],
            )
        if not subgroup_summaries:
            subgroup_summaries = None

    png = render_forest_png(
        rows=rows,
        pooled_estimate=pooled.estimate,
        pooled_ci_low=pooled.ci_low,
        pooled_ci_high=pooled.ci_high,
        metric_label=metric_label,
        log_scale=log_scale,
        favours_left=None,
        favours_right=None,
        subgroup_summaries=subgroup_summaries,
    )
    return Response(content=png, media_type="image/png", headers={"Cache-Control": "no-store"})


@router.get("/projects/{project_id}/reviews/meta/{meta_id}/funnel.png")
async def get_funnel_png(
    project_id: str,
    meta_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> Response:
    meta, inputs = await _load_meta_for_plot(project_id, meta_id, session, user_id)
    effects = [_input_to_effect(meta.effect_metric, inp) for inp in inputs]
    metric_label = _METRIC_LABELS.get(meta.effect_metric, meta.effect_metric)
    log_scale = meta.effect_metric in _LOG_SCALE_METRICS
    png = render_funnel_png(
        effects=effects,
        pooled_estimate=meta.pooled_estimate or 0.0,
        metric_label=metric_label,
        log_scale=log_scale,
    )
    return Response(content=png, media_type="image/png", headers={"Cache-Control": "no-store"})


# ── Interpret ──────────────────────────────────────────────────────────


@router.post(
    "/projects/{project_id}/reviews/meta/{meta_id}/interpret",
    response_model=MetaAnalysisRead,
)
async def interpret_meta_analysis(
    project_id: str,
    meta_id: str,
    container: Container = Depends(get_container),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> MetaAnalysisRead:
    _, review = await _resolve_review(project_id, session, user_id)
    repo = SqliteMetaRepository(session)
    pair = await repo.get_with_inputs(meta_id, user_id)
    if pair is None or pair[0].review_id != review.id:
        raise HTTPException(status_code=404, detail="Meta-analysis not found")
    meta, inputs = pair
    if meta.status != "completed":
        raise HTTPException(status_code=422, detail="Run the analysis before interpretation")

    art_repo = SqliteArticleRepository(session)
    studies: list[dict[str, str]] = []
    for inp in inputs:
        label = inp.study_label
        if not label:
            art = await art_repo.get(inp.article_id, user_id)
            label = art.title if art else inp.article_id
        studies.append({"article_id": inp.article_id, "label": label})

    pooled = {
        "estimate": meta.pooled_estimate,
        "se": meta.pooled_se,
        "ci_low": meta.ci_low,
        "ci_high": meta.ci_high,
        "z": meta.z_value,
        "p": meta.p_value,
    }
    het = {
        "q": meta.q_value,
        "q_df": meta.q_df,
        "q_p": meta.q_p,
        "i2": meta.i2,
        "tau2": meta.tau2,
    }
    subgroups = meta.subgroup_summary or None

    try:
        prose = await container.ai.interpret_meta_analysis(
            metric=meta.effect_metric,
            model=meta.model,
            pooled=pooled,
            heterogeneity=het,
            studies=studies,
            subgroups=subgroups,
        )
    except (AIProviderUnavailable, AIRateLimited, AISourceInsufficient, AIError) as exc:
        raise _map_ai_error(exc) from None
    except Exception:
        log.exception("Unexpected AI error in interpret_meta_analysis")
        raise HTTPException(status_code=503, detail="AI provider unavailable") from None

    await repo.write_interpretation(meta_id=meta_id, user_id=user_id, prose=prose)
    fresh = await repo.get(meta_id, user_id)
    fresh_inputs = await repo.list_inputs(meta_id, user_id)
    return _hydrate_meta(fresh, fresh_inputs)


# ── Push to manuscript Results section ─────────────────────────────────


@router.post(
    "/projects/{project_id}/reviews/meta/{meta_id}/push",
    response_model=ManuscriptSectionRead,
)
async def push_meta_to_results(
    project_id: str,
    meta_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> ManuscriptSectionRead:
    meta, inputs = await _load_meta_for_plot(project_id, meta_id, session, user_id)
    rows, pooled, _ = _build_forest_rows_and_pooled(meta, inputs)
    metric_label = _METRIC_LABELS.get(meta.effect_metric, meta.effect_metric)
    log_scale = meta.effect_metric in _LOG_SCALE_METRICS

    subgroup_summaries: dict[str, tuple[float, float, float]] | None = None
    if meta.subgroup_summary:
        subgroup_summaries = {}
        for sg, payload in meta.subgroup_summary.items():
            if payload.get("estimate") is None:
                continue
            subgroup_summaries[sg] = (
                payload["estimate"],
                payload["ci_low"],
                payload["ci_high"],
            )
        if not subgroup_summaries:
            subgroup_summaries = None

    png = render_forest_png(
        rows=rows,
        pooled_estimate=pooled.estimate,
        pooled_ci_low=pooled.ci_low,
        pooled_ci_high=pooled.ci_high,
        metric_label=metric_label,
        log_scale=log_scale,
        favours_left=None,
        favours_right=None,
        subgroup_summaries=subgroup_summaries,
    )
    b64 = base64.b64encode(png).decode("ascii")
    alt = f"Forest plot for {meta.title or metric_label}"

    if meta.ai_interpretation:
        # The AI prose is expected to carry the [CITE_xxx] tokens; do NOT escape it as untrusted HTML.
        caption_html = meta.ai_interpretation
    else:
        # Deterministic fallback caption — escape any researcher-controlled strings.
        i2 = f"{meta.i2:.1f}" if meta.i2 is not None else "n/a"
        caption = (
            f"Forest plot for {metric_label} "
            f"({meta.model}-effects model, k={len(inputs)}, I²={i2}%)."
        )
        tokens = " ".join(f"[CITE_{escape(inp.article_id)}]" for inp in inputs)
        caption_html = f"{escape(caption)} <small>{tokens}</small>"

    # Resolve `[CITE_<aid>]` tokens carried in the AI prose (or the
    # deterministic fallback) so the manuscript never persists raw tokens.
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    style: CitationStyle = (
        project.citation_style if project is not None
        and project.citation_style in ("vancouver", "apa", "harvard", "ieee")
        else "vancouver"
    )  # type: ignore[assignment]
    art_repo = SqliteArticleRepository(session)
    articles_by_tag: dict[str, object] = {}
    for inp in inputs:
        art = await art_repo.get(inp.article_id, user_id)
        if art is not None:
            articles_by_tag[inp.article_id] = art

    numbering: dict[str, int] | None = None
    if style == "ieee":
        # Number based on existing Results-section content so re-pushes keep
        # the same N for already-cited articles, and new pooled studies pick
        # up the next free numbers.
        sec_repo = SqliteManuscriptSectionRepository(session)
        prior = await sec_repo.list_for_project(project_id, user_id)
        existing_ids = collect_used_article_ids_in_order(prior)
        numbering = {aid: i + 1 for i, aid in enumerate(existing_ids)}
        next_n = len(existing_ids) + 1
        for inp in inputs:
            if inp.article_id not in numbering and inp.article_id in articles_by_tag:
                numbering[inp.article_id] = next_n
                next_n += 1

    caption_html = replace_cite_tokens_with_markup(
        caption_html,
        articles_by_tag,
        style=style,
        numbering=numbering,
    )

    html = (
        '<figure class="meta-analysis-forest">'
        f'<img src="data:image/png;base64,{b64}" alt="{escape(alt)}"/>'
        f"<figcaption>{caption_html}</figcaption>"
        "</figure>"
    )
    return await _push_to_section(
        session,
        project_id=project_id,
        section_name="Results",
        html=html,
        class_hook="meta-analysis-forest",
        user_id=user_id,
    )
