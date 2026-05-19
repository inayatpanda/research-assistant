"""Phase 13 — Power calculator endpoint.

Stateless: no DB writes; the user supplies effect size + alpha + power and
gets back a required-n + sensitivity-curve PNG (data URI). The endpoint is
scoped per local user only because there is no resource to scope against.
"""
from __future__ import annotations

import base64

from fastapi import APIRouter, HTTPException

from ..schemas.power import PowerRequest, PowerResponse
from ..services.stats.power import (
    power_anova,
    power_chi_square,
    power_correlation,
    power_logrank,
    power_mixed_effects,
    power_noninferiority,
    power_ttest_ind,
    power_ttest_paired,
)

router = APIRouter(tags=["power"])


def _to_data_uri(png: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")


@router.post("/power", response_model=PowerResponse)
async def compute_power(body: PowerRequest) -> PowerResponse:
    try:
        if body.test_family == "ttest_ind":
            result = power_ttest_ind(body.effect_size, alpha=body.alpha, power=body.power)
        elif body.test_family == "ttest_paired":
            result = power_ttest_paired(body.effect_size, alpha=body.alpha, power=body.power)
        elif body.test_family == "anova":
            if body.k_groups is None:
                raise HTTPException(status_code=400, detail="ANOVA requires k_groups (>= 2)")
            result = power_anova(
                body.effect_size,
                k_groups=body.k_groups,
                alpha=body.alpha,
                power=body.power,
            )
        elif body.test_family == "chi_square":
            if body.df is None:
                raise HTTPException(status_code=400, detail="chi_square requires df (>= 1)")
            result = power_chi_square(
                body.effect_size,
                df=body.df,
                alpha=body.alpha,
                power=body.power,
            )
        elif body.test_family == "correlation":
            result = power_correlation(
                body.effect_size, alpha=body.alpha, power=body.power
            )
        elif body.test_family == "logrank":
            if body.event_rate is None:
                raise HTTPException(status_code=400, detail="logrank requires event_rate")
            result = power_logrank(
                body.effect_size,
                alpha=body.alpha,
                power=body.power,
                allocation_ratio=body.allocation_ratio or 1.0,
                event_rate=body.event_rate,
            )
        elif body.test_family == "mixed_effects":
            if body.n_per_cluster is None or body.n_clusters is None or body.icc is None:
                raise HTTPException(
                    status_code=400,
                    detail="mixed_effects requires n_per_cluster, n_clusters, and icc",
                )
            result = power_mixed_effects(
                body.effect_size,
                n_per_cluster=body.n_per_cluster,
                n_clusters=body.n_clusters,
                icc=body.icc,
                alpha=body.alpha,
                power=body.power,
            )
        elif body.test_family == "noninferiority":
            if body.sigma is None:
                raise HTTPException(status_code=400, detail="noninferiority requires sigma")
            result = power_noninferiority(
                body.effect_size,
                sigma=body.sigma,
                alpha=body.alpha,
                power=body.power,
                allocation_ratio=body.allocation_ratio or 1.0,
            )
        else:  # pragma: no cover - Literal exhaustiveness
            raise HTTPException(status_code=400, detail=f"unknown test_family {body.test_family}")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None

    return PowerResponse(
        required_n=result["required_n"],
        required_n_per_group=result["required_n_per_group"],
        alpha=result["alpha"],
        power=result["power"],
        effect_size=result["effect_size"],
        sensitivity_curve_png=_to_data_uri(result["sensitivity_curve_png"]),
        notes=result["notes"],
        required_events=result.get("required_events"),
        required_clusters_per_arm=result.get("required_clusters_per_arm"),
        design_effect=result.get("design_effect"),
    )
