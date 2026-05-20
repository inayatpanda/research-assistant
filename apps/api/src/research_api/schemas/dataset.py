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
    # Phase 17 (MP17) — Optional binding to the instrument catalogue.
    instrument_key: str | None = None
    # DEMO-FIX-C — Free-text display label used by charts/AI/exports.
    # Defaults to the canonical name when no override has been set.
    display_label: str | None = None


class DatasetVariableUpdate(BaseModel):
    user_type: VariableType | None


class DatasetVariableDisplayLabelUpdate(BaseModel):
    """DEMO-FIX-C — Body for PATCH .../variables/{vid}/display-label."""

    display_label: str


class HeaderSanitisationEntry(BaseModel):
    """DEMO-FIX-C — One row of the upload sanitisation report."""

    original: str
    sanitised: str


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
    # Phase 13 (MP13) — Cross-dataset ops can derive from 2+ sources.
    derived_from_dataset_ids: list[str] | None = None
    # DEMO-FIX-C — When upload had to rename any non-conforming headers,
    # the report lists every (original, sanitised) pair. Empty/omitted
    # when no renames were needed.
    header_sanitisation_report: list[HeaderSanitisationEntry] = []
