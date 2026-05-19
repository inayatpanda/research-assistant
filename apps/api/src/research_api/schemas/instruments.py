"""Phase 17 (MP17) — Outcome-instrument catalogue + binding schemas."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

InstrumentDirection = Literal["higher_better", "lower_better", "neutral"]
InstrumentCategory = Literal[
    "hip_knee", "spine", "shoulder_elbow", "foot_ankle", "generic", "cardio"
]


class InstrumentSpec(BaseModel):
    """A row in the curated 30-item declarative catalogue (read-only)."""

    model_config = ConfigDict(frozen=True)

    name: str
    abbreviation: str
    scale_low: float
    scale_high: float
    mid: float | None
    direction: InstrumentDirection
    category: InstrumentCategory
    default_citation: str


class InstrumentCatalogueResponse(BaseModel):
    instruments: list[InstrumentSpec]


class InstrumentBindingRequest(BaseModel):
    """PATCH body to bind a dataset variable to an instrument key (or unbind
    with ``null``). The key must match one of the catalogue's abbreviations."""

    instrument_key: str | None = Field(default=None, max_length=64)


class InstrumentBindingRead(BaseModel):
    variable_id: str
    instrument_key: str | None
