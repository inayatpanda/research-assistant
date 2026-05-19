"""Meta-analysis extensions: publication bias / leave-one-out / Q-between /
meta-regression (Phase 19 / MP19).

These endpoints sit alongside ``reviews_meta.py`` and reuse the same
``_resolve_review`` / ``_input_to_effect`` helpers via a thin import.
"""
from __future__ import annotations

import base64
import logging
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..container import Container, get_container
from ..repositories.meta import SqliteMetaRepository
from ..repositories.projects import SqliteProjectRepository
from ..repositories.reviews import SqliteReviewRepository
from ..services.meta import effect_sizes as es
from ..services.meta.leave_one_out import (
    LeaveOneOutRow,
    leave_one_out,
    render_leave_one_out_png,
)
from ..services.meta.meta_regression import meta_regression
from ..services.meta.publication_bias import (
    BiasResult,
    begg_test,
    egger_test,
    harbord_test,
    peters_test,
    select_test_for_metric,
)
from ..services.meta.subgroup_interaction import subgroup_q_between
from .reviews_meta import _input_to_effect

router = APIRouter(tags=["meta-extensions"])
log = logging.getLogger("research_api.meta_extensions")


async def _session(
    container: Container = Depends(get_container),
) -> AsyncIterator[AsyncSession]:
    async with container.session_factory() as s:
        yield s


def _user_id(container: Container = Depends(get_container)) -> str:
    return container.settings.local_user_id


async def _resolve_meta(project_id: str, meta_id: str, session: AsyncSession, user_id: str):
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    review_repo = SqliteReviewRepository(session)
    review = await review_repo.get_or_create(project_id=project_id, user_id=user_id)
    repo = SqliteMetaRepository(session)
    pair = await repo.get_with_inputs(meta_id, user_id)
    if pair is None or pair[0].review_id != review.id:
        raise HTTPException(status_code=404, detail="Meta-analysis not found")
    return pair


def _bias_dict(result: BiasResult) -> dict[str, Any]:
    return {
        "method": result.method,
        "statistic": result.statistic,
        "p": result.p,
        "note": result.note,
    }


# ── Publication bias ───────────────────────────────────────────────────


@router.get("/projects/{project_id}/reviews/meta/{meta_id}/publication-bias")
async def publication_bias_route(
    project_id: str,
    meta_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> dict:
    meta, inputs = await _resolve_meta(project_id, meta_id, session, user_id)
    if len(inputs) < 3:
        raise HTTPException(
            status_code=422,
            detail="Publication-bias tests require at least 3 studies",
        )
    metric = meta.effect_metric
    effects = []
    for inp in inputs:
        try:
            effects.append(_input_to_effect(metric, inp))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from None
    ys = [e.yi for e in effects]
    ses_ = [e.se for e in effects]

    result_blob: dict[str, Any] = {
        "metric": metric,
        "k": len(effects),
        "recommended": select_test_for_metric(metric),
        "tests": [],
    }
    try:
        result_blob["tests"].append(_bias_dict(egger_test(ys, ses_)))
    except ValueError as exc:
        result_blob["tests"].append(
            {"method": "egger", "statistic": None, "p": None, "note": str(exc)}
        )
    if len(effects) >= 4:
        try:
            result_blob["tests"].append(_bias_dict(begg_test(ys, ses_)))
        except ValueError as exc:
            result_blob["tests"].append(
                {"method": "begg", "statistic": None, "p": None, "note": str(exc)}
            )
    else:
        result_blob["tests"].append(
            {"method": "begg", "statistic": None, "p": None, "note": "Begg requires ≥ 4 studies"}
        )
    if metric in {"or", "rr"}:
        try:
            events_t = [inp.events_a or 0 for inp in inputs]
            n_t = [inp.n_a_total or 0 for inp in inputs]
            events_c = [inp.events_b or 0 for inp in inputs]
            n_c = [inp.n_b_total or 0 for inp in inputs]
            result_blob["tests"].append(
                _bias_dict(harbord_test(events_t, n_t, events_c, n_c))
            )
        except ValueError as exc:
            result_blob["tests"].append(
                {"method": "harbord", "statistic": None, "p": None, "note": str(exc)}
            )
        try:
            events = [
                (inp.events_a or 0) + (inp.events_b or 0) for inp in inputs
            ]
            totals = [
                (inp.n_a_total or 0) + (inp.n_b_total or 0) for inp in inputs
            ]
            log_or_list = [e.yi for e in effects]
            result_blob["tests"].append(
                _bias_dict(peters_test(events, totals, log_or=log_or_list))
            )
        except ValueError as exc:
            result_blob["tests"].append(
                {"method": "peters", "statistic": None, "p": None, "note": str(exc)}
            )
    return result_blob


# ── Leave-one-out ──────────────────────────────────────────────────────


@router.get("/projects/{project_id}/reviews/meta/{meta_id}/leave-one-out")
async def leave_one_out_route(
    project_id: str,
    meta_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> dict:
    meta, inputs = await _resolve_meta(project_id, meta_id, session, user_id)
    if len(inputs) < 3:
        raise HTTPException(
            status_code=422, detail="Leave-one-out requires at least 3 studies"
        )
    effects: list[es.Effect] = []
    ids: list[str] = []
    for inp in inputs:
        try:
            effects.append(_input_to_effect(meta.effect_metric, inp))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from None
        ids.append(inp.study_label or inp.article_id)
    rows = leave_one_out(effects, ids=ids, model=meta.model)
    return {
        "model": meta.model,
        "metric": meta.effect_metric,
        "k": len(effects),
        "rows": [
            {
                "excluded_id": r.excluded_id,
                "pooled_effect": r.pooled_effect,
                "ci_low": r.ci_low,
                "ci_high": r.ci_high,
                "i2": r.i2,
            }
            for r in rows
        ],
    }


@router.get("/projects/{project_id}/reviews/meta/{meta_id}/leave-one-out.png")
async def leave_one_out_png_route(
    project_id: str,
    meta_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> Response:
    meta, inputs = await _resolve_meta(project_id, meta_id, session, user_id)
    if len(inputs) < 3:
        raise HTTPException(
            status_code=422, detail="Leave-one-out requires at least 3 studies"
        )
    if meta.status != "completed" or meta.pooled_estimate is None:
        raise HTTPException(status_code=409, detail="Run the analysis first")
    effects: list[es.Effect] = []
    ids: list[str] = []
    for inp in inputs:
        try:
            effects.append(_input_to_effect(meta.effect_metric, inp))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from None
        ids.append(inp.study_label or inp.article_id)
    rows: list[LeaveOneOutRow] = leave_one_out(effects, ids=ids, model=meta.model)
    log_scale = meta.effect_metric in {"or", "rr", "hr"}
    png = render_leave_one_out_png(
        rows,
        overall_estimate=meta.pooled_estimate,
        metric_label=meta.effect_metric.upper(),
        log_scale=log_scale,
    )
    return Response(
        content=png,
        media_type="image/png",
        headers={"Cache-Control": "no-store"},
    )


# ── Subgroup Q-between ─────────────────────────────────────────────────


@router.get("/projects/{project_id}/reviews/meta/{meta_id}/subgroup-interaction")
async def subgroup_interaction_route(
    project_id: str,
    meta_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> dict:
    meta, inputs = await _resolve_meta(project_id, meta_id, session, user_id)
    if not meta.subgroup_variable:
        raise HTTPException(
            status_code=422, detail="Meta-analysis has no subgroup variable"
        )
    groups: dict[str, list[es.Effect]] = {}
    for inp in inputs:
        try:
            eff = _input_to_effect(meta.effect_metric, inp)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from None
        sg = inp.subgroup or "Unspecified"
        groups.setdefault(sg, []).append(eff)
    try:
        result = subgroup_q_between(groups)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return {
        "q_between": result.q_between,
        "df": result.df,
        "p_interaction": result.p_interaction,
    }


# ── Meta-regression ────────────────────────────────────────────────────


class MetaRegressionRequest(BaseModel):
    moderator: list[float] = Field(min_length=3)
    moderator_label: str = "Moderator"
    model: str | None = None  # falls back to meta.model


@router.post("/projects/{project_id}/reviews/meta/{meta_id}/meta-regression")
async def meta_regression_route(
    project_id: str,
    meta_id: str,
    body: MetaRegressionRequest = Body(...),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> dict:
    meta, inputs = await _resolve_meta(project_id, meta_id, session, user_id)
    if len(inputs) != len(body.moderator):
        raise HTTPException(
            status_code=422,
            detail=(
                f"Moderator length ({len(body.moderator)}) must match number "
                f"of inputs ({len(inputs)})"
            ),
        )
    effects: list[es.Effect] = []
    for inp in inputs:
        try:
            effects.append(_input_to_effect(meta.effect_metric, inp))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from None
    try:
        result = meta_regression(
            effects,
            body.moderator,
            model=body.model or meta.model,
            moderator_label=body.moderator_label,
            metric_label=meta.effect_metric.upper(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return {
        "intercept": result.intercept,
        "coef": result.coef,
        "se": result.se,
        "p": result.p,
        "r2": result.r2,
        "n": result.n,
        "bubble_plot_png_base64": base64.b64encode(
            result.bubble_plot_png
        ).decode("ascii"),
    }
