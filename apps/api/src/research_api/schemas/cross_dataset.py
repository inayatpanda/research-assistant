"""Phase 13 (MP13) — Cross-dataset op request / response schemas."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

CrossOpName = Literal["merge", "append", "join"]


class CrossOpRequest(BaseModel):
    op: CrossOpName
    source_dataset_ids: list[str] = Field(..., min_length=1)
    args: dict[str, Any] = Field(default_factory=dict)
    # Optional override filename for the result; default is auto-generated.
    filename: str | None = None


class CrossOpResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    dataset_id: str
    filename: str
    n_rows: int
    n_columns: int
    source_dataset_ids: list[str]
