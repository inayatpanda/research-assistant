from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

VariableType = Literal[
    "numeric",
    "ordinal",
    "nominal",
    "time",
    "event_indicator",
    "unknown",
]


class DatasetVariableRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    dataset_id: str
    name: str
    position: int
    inferred_type: VariableType
    user_type: VariableType | None
    n_missing: int
    sample_values: list[str]


class DatasetVariableUpdate(BaseModel):
    user_type: VariableType | None


class DatasetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    filename: str
    file_type: str
    n_rows: int
    n_columns: int
    created_at: datetime
    variables: list[DatasetVariableRead] = []
    # Phase 13 — PSM-derived datasets point back to their source + carry
    # the covariate-balance JSON.
    derived_from_dataset_id: str | None = None
    dataset_metadata: dict[str, Any] | None = None
