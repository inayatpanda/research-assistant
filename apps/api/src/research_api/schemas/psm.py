"""Phase 13 — PSM request/response schemas."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PSMRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    treatment_col: str = Field(min_length=1)
    covariate_cols: list[str] = Field(min_length=1)
    caliper_sd: float = Field(default=0.2, gt=0.0, le=2.0)


class CovariateBalanceRow(BaseModel):
    covariate: str
    smd: float
    mean_treated: float
    mean_control: float


class PSMResponse(BaseModel):
    matched_dataset_id: str
    n_treated_total: int
    n_control_total: int
    n_treated_matched: int
    n_control_matched: int
    caliper_sd: float
    balance_before: list[CovariateBalanceRow]
    balance_after: list[CovariateBalanceRow]
    max_smd_before: float
    max_smd_after: float
