"""Phase 13.5 (MP13.5) — Analysis plan + plan run Pydantic schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

StepType = Literal["transform", "test", "plot"]
RunStatus = Literal["ok", "partial", "failed"]
StepStatus = Literal["ok", "failed"]


class PlanStep(BaseModel):
    """A single step in an analysis plan.

    For ``transform``: ``args`` carries ``op_type`` + ``op_args`` (mirrors
    DatasetTransformation.op_args).
    For ``test``: ``args`` carries ``test_key``, ``question_type``, and
    ``variables`` (variable name map).
    For ``plot``: ``args`` carries a full PlotSpec dict (geom, x, y, …).
    """

    type: StepType
    args: dict[str, Any] = Field(default_factory=dict)


class AnalysisPlanCreate(BaseModel):
    name: str
    description: str | None = None
    steps: list[PlanStep] = Field(default_factory=list)


class AnalysisPlanUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    steps: list[PlanStep] | None = None


class AnalysisPlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    name: str
    description: str | None
    steps: list[dict[str, Any]]
    created_at: datetime
    updated_at: datetime


class AnalysisPlanRunRequest(BaseModel):
    dataset_id: str


class StepResult(BaseModel):
    step_index: int
    type: StepType
    status: StepStatus
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class AnalysisPlanRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    plan_id: str
    dataset_id: str
    executed_at: datetime
    result_blob: dict[str, Any]
    status: RunStatus
    error: str | None = None
