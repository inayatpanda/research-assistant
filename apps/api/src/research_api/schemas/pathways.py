"""F3 — Pydantic schemas for the Research Pathways endpoints.

Each request only carries the dataset column references; the route
fetches the dataset bytes, applies any transformation stack, then hands
the in-memory DataFrame to the relevant orchestrator under
``services.pathways``.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

PathwayKey = Literal[
    "two-group",
    "risk-factors",
    "survival",
    "diagnostic",
    "agreement",
]


class TwoGroupRequest(BaseModel):
    outcome: str
    group: str


class RiskFactorsRequest(BaseModel):
    outcome: str
    predictors: list[str] = Field(..., min_length=1)
    confounders: list[str] | None = None


class SurvivalRequest(BaseModel):
    time: str
    event: str
    strata: str | None = None
    predictors: list[str] | None = None


class DiagnosticRequest(BaseModel):
    test: str
    reference: str
    pre_test_probability: float | None = None


class AgreementRequest(BaseModel):
    rater_a: str
    rater_b: str
    ordinal: bool | None = None


class PathwayProse(BaseModel):
    methods: str
    results: str


class PathwayResponse(BaseModel):
    pathway: PathwayKey
    result: dict[str, Any]
    prose: PathwayProse


class PathwayPushRequest(BaseModel):
    pathway: PathwayKey
    target: Literal["methods", "results", "both"] = "both"
    methods: str | None = None
    results: str | None = None


__all__ = [
    "AgreementRequest",
    "DiagnosticRequest",
    "PathwayKey",
    "PathwayProse",
    "PathwayPushRequest",
    "PathwayResponse",
    "RiskFactorsRequest",
    "SurvivalRequest",
    "TwoGroupRequest",
]
