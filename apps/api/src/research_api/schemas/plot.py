"""Phase 13.5 (MP13.5) — Dataset plot Pydantic schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Geom = Literal[
    "point",
    "bar",
    "line",
    "box",
    "violin",
    "heatmap",
    "histogram",
    "density",
    "pair",
]


class PlotSpec(BaseModel):
    """Grammar-of-graphics spec.

    Not every geom uses every channel; the renderer dispatches on ``geom``
    and pulls the channels it needs:

      - point/line: x + y (+ optional color/facet)
      - bar: x (+ optional y for value; defaults to count)
      - box/violin: x (categorical) + y (numeric)
      - heatmap: x + y + value (in args["value"])
      - histogram/density: x only
      - pair: x is ignored; uses args["columns"] (list of numeric col names)
    """

    geom: Geom
    x: str | None = None
    y: str | None = None
    color: str | None = None
    facet: str | None = None
    args: dict[str, Any] = Field(default_factory=dict)


class PlotCreate(BaseModel):
    geom: Geom
    x: str | None = None
    y: str | None = None
    color: str | None = None
    facet: str | None = None
    args: dict[str, Any] = Field(default_factory=dict)
    title: str = ""


class PlotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    dataset_id: str
    title: str
    spec: dict[str, Any]
    png_data_uri: str
    created_at: datetime
    updated_at: datetime
