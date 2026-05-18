"""Phase 13 — Power calculator request/response schemas."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

TestFamily = Literal[
    "ttest_ind",
    "ttest_paired",
    "anova",
    "chi_square",
    "correlation",
]


class PowerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    test_family: TestFamily
    effect_size: float = Field(gt=0.0, description="Cohen's d / dz / f / w / |r|")
    alpha: float = Field(default=0.05, gt=0.0, lt=1.0)
    power: float = Field(default=0.80, gt=0.0, lt=1.0)
    k_groups: int | None = Field(default=None, ge=2, description="ANOVA only")
    df: int | None = Field(default=None, ge=1, description="Chi-square only (bins - 1)")


class PowerResponse(BaseModel):
    required_n: int
    required_n_per_group: int | None
    alpha: float
    power: float
    effect_size: float
    sensitivity_curve_png: str  # data URI
    notes: str
