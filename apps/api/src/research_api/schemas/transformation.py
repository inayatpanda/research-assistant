"""Phase 13 (MP13) — DatasetTransformation Pydantic schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

OpType = Literal[
    "filter",
    "mutate",
    "select",
    "recode",
    "drop_na",
    "log_transform",
    "z_score",
    "group_summarise",
]


class TransformationCreate(BaseModel):
    op_type: OpType
    op_args: dict[str, Any] = Field(default_factory=dict)
    label: str = ""
    # Optional: place at a specific position; default = append at end.
    position: int | None = None


class TransformationUpdate(BaseModel):
    op_args: dict[str, Any] | None = None
    label: str | None = None
    position: int | None = None


class TransformationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    dataset_id: str
    position: int
    op_type: OpType
    op_args: dict[str, Any]
    label: str
    created_at: datetime


class TransformationReorderRequest(BaseModel):
    """Replace the full ordering with this id sequence (transactional)."""

    ids: list[str]
