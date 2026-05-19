"""Phase 17 (MP17) — ImputationRun Pydantic schemas + sensitivity/CACE bodies."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

ImputationMethod = Literal[
    "mice", "knn", "mean", "median", "last_observation"
]


class ImputationRunRequest(BaseModel):
    method: ImputationMethod = "mice"
    target_cols: list[str] = Field(min_length=1)
    n_imputations: int = Field(default=5, ge=1, le=20)
    seed: int = Field(default=42, ge=0)


class ImputationRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    dataset_id: str
    method: str
    n_imputations: int
    seed: int
    target_cols: list[str]
    pooled_summary: dict[str, Any]
    created_at: datetime


class CACERequest(BaseModel):
    """2SLS body. ``assigned`` is the randomised group; ``received`` the
    actual treatment received; ``outcome`` the response variable."""

    outcome: str
    assigned: str
    received: str


class CACEResponse(BaseModel):
    cace_estimate: float
    se: float
    p: float
    compliance_rate: float
    n: int


class SensitivityRequest(BaseModel):
    type: Literal["worst_case", "best_case", "tipping_point"]
    outcome: str
    group: str
    # tipping_point: candidate values to bisect over (numeric column only).
    candidate_low: float | None = None
    candidate_high: float | None = None
    alpha: float = Field(default=0.05, gt=0, lt=1)


class SensitivityResponse(BaseModel):
    type: str
    effect_estimate: float | None
    p_value: float | None
    threshold: float | None = None  # tipping point
    n_imputed: int
    note: str
