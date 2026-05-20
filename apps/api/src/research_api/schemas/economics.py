"""Phase 18 (MP18) — Pydantic schemas for the Health Economics module."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


Currency = Literal["GBP", "USD", "EUR", "AUD", "CAD", "Other"]
Perspective = Literal["patient", "healthcare_system", "societal"]
UtilityValueSet = Literal[
    "EQ5D_3L_UK", "EQ5D_5L_UK", "EQ5D_Y_DUTCH", "SF6D", "direct"
]
CostRole = Literal[
    "unit_cost",
    "quantity",
    "cost_total",
    "utility_score",
    "qaly_weight",
    "time_to_event",
]
DominanceStatus = Literal[
    "dominant", "dominated", "icer_calculated", "northeast", "southwest"
]
SensitivityKind = Literal["psa", "dsa", "scenario"]


class CostColumnBinding(BaseModel):
    """A single (column, role) binding inside ``cost_columns``."""

    col: str = Field(min_length=1, max_length=255)
    role: CostRole


class EconomicAnalysisCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    dataset_id: str | None = Field(default=None, max_length=32)
    currency: Currency = "GBP"
    time_horizon_months: int = Field(default=12, ge=1, le=600)
    perspective: Perspective = "healthcare_system"
    discount_rate_costs: float = Field(default=0.035, ge=0.0, le=0.5)
    discount_rate_qalys: float = Field(default=0.035, ge=0.0, le=0.5)
    wtp_thresholds: list[int] = Field(default_factory=lambda: [20000, 30000])
    utility_value_set: UtilityValueSet = "EQ5D_5L_UK"
    bootstrap_n: int = Field(default=1000, ge=100, le=10000)
    seed: int = Field(default=42, ge=0)
    treatment_col: str = Field(min_length=1, max_length=255)
    comparator_label: str = Field(min_length=1, max_length=255)
    intervention_label: str = Field(min_length=1, max_length=255)
    cost_columns: list[CostColumnBinding] = Field(default_factory=list)

    @field_validator("wtp_thresholds")
    @classmethod
    def _check_thresholds(cls, v: list[int]) -> list[int]:
        if not v:
            raise ValueError("at least one WTP threshold required")
        if any(x < 0 for x in v):
            raise ValueError("WTP thresholds must be non-negative")
        return sorted(set(int(x) for x in v))


class EconomicAnalysisUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    dataset_id: str | None = Field(default=None, max_length=32)
    currency: Currency | None = None
    time_horizon_months: int | None = Field(default=None, ge=1, le=600)
    perspective: Perspective | None = None
    discount_rate_costs: float | None = Field(default=None, ge=0.0, le=0.5)
    discount_rate_qalys: float | None = Field(default=None, ge=0.0, le=0.5)
    wtp_thresholds: list[int] | None = None
    utility_value_set: UtilityValueSet | None = None
    bootstrap_n: int | None = Field(default=None, ge=100, le=10000)
    seed: int | None = Field(default=None, ge=0)
    treatment_col: str | None = Field(default=None, max_length=255)
    comparator_label: str | None = Field(default=None, max_length=255)
    intervention_label: str | None = Field(default=None, max_length=255)
    cost_columns: list[CostColumnBinding] | None = None


class CEACPoint(BaseModel):
    wtp: float
    prob_costeffective: float


class PlanePoint(BaseModel):
    dCost: float
    dQALY: float


class EconomicResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    economic_analysis_id: str
    mean_cost_diff: float
    mean_qaly_diff: float
    icer: float | None
    dominance_status: str
    nmb_at_thresholds: dict[str, Any]
    ceac_data: list[dict[str, Any]]
    plane_bootstrap: list[dict[str, Any]]
    sensitivity: dict[str, Any] | None
    plane_png_uri: str
    ceac_png_uri: str
    created_at: datetime


class EconomicAnalysisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    dataset_id: str | None
    name: str
    currency: str
    time_horizon_months: int
    perspective: str
    discount_rate_costs: float
    discount_rate_qalys: float
    wtp_thresholds: list[int]
    utility_value_set: str
    bootstrap_n: int
    seed: int
    treatment_col: str
    comparator_label: str
    intervention_label: str
    cost_columns: list[dict[str, Any]]
    ai_interpretation: str | None
    created_at: datetime
    updated_at: datetime
    result: EconomicResultRead | None = None


class SensitivityRequest(BaseModel):
    """Body for /sensitivity?type=...

    For PSA: parameter_distributions = {param: {dist, ...kwargs}}.
    For DSA: parameter_ranges = {param: {low, high}}.
    For scenario: scenarios = [{name, overrides: {param: value}}].
    """

    parameter_distributions: dict[str, dict[str, Any]] | None = None
    parameter_ranges: dict[str, dict[str, float]] | None = None
    scenarios: list[dict[str, Any]] | None = None
    n_psa: int = Field(default=1000, ge=100, le=10000)
    seed: int = Field(default=42, ge=0)


class PushEconomicRequest(BaseModel):
    """Body for the push-to-manuscript endpoint."""

    section: str = Field(default="Results", max_length=64)


class UtilityValueSetInfo(BaseModel):
    """Static catalogue entry returned by GET /api/utility-value-sets."""

    key: str
    label: str
    dimensions: list[str]
    levels: int
    source_citation: str
    notes: str | None = None
