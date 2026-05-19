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
    # Phase 17 (MP17) — Extended power families.
    "logrank",
    "mixed_effects",
    "noninferiority",
]


class PowerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    test_family: TestFamily
    # ``effect_size`` is overloaded across families:
    #   ttest_ind/paired: Cohen's d/dz; anova: f; chi_square: w; correlation: |r|;
    #   logrank: hazard_ratio; mixed_effects: Cohen's d at the cluster level;
    #   noninferiority: the margin (must be > 0 — on the same scale as sigma).
    effect_size: float = Field(gt=0.0, description="Family-specific effect size")
    alpha: float = Field(default=0.05, gt=0.0, lt=1.0)
    power: float = Field(default=0.80, gt=0.0, lt=1.0)
    k_groups: int | None = Field(default=None, ge=2, description="ANOVA only")
    df: int | None = Field(default=None, ge=1, description="Chi-square only (bins - 1)")
    # Phase 17 (MP17) — Extra parameters per family (all optional; validated
    # at the route layer).
    event_rate: float | None = Field(default=None, gt=0.0, le=1.0, description="logrank")
    allocation_ratio: float | None = Field(default=None, gt=0.0)
    n_per_cluster: int | None = Field(default=None, ge=1, description="mixed_effects")
    n_clusters: int | None = Field(default=None, ge=2, description="mixed_effects")
    icc: float | None = Field(default=None, ge=0.0, le=1.0, description="mixed_effects")
    sigma: float | None = Field(default=None, gt=0.0, description="noninferiority")


class PowerResponse(BaseModel):
    required_n: int
    required_n_per_group: int | None
    alpha: float
    power: float
    effect_size: float
    sensitivity_curve_png: str  # data URI
    notes: str
    # Phase 17 (MP17) — Optional extras returned by some families.
    required_events: int | None = None  # logrank
    required_clusters_per_arm: int | None = None  # mixed_effects
    design_effect: float | None = None  # mixed_effects
