"""Phase 4.5 — Articles-table schemas.

Schemas for the manuscript-editor's "Insert articles table" feature. The
frontend collects a list of articles + column presets via a dialog, the
backend renders the matching HTML, and the editor inserts it via
``editor.commands.insertContent``.

No DB columns / no migration — this is a stateless render service. The
preset list is intentionally small and pragmatic; custom columns fill the
gaps the user needs but we don't catalogue them.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# Column presets the backend knows how to render from articles +
# extraction_records. The first preset (``author_year_citation``) is the
# locked first column and is always rendered. Other presets pull from
# ``Article`` directly or, where relevant, from the active review's
# ``ExtractionRecord.fields`` JSON (best-effort; empty cell on miss).
ColumnPreset = Literal[
    "author_year_citation",
    "title",
    "journal",
    "year",
    "country",
    "study_design",
    "sample_size_n",
    "intervention",
    "comparator",
    "primary_outcome",
    "follow_up",
    "effect_estimate",
    "risk_of_bias_rating",
    "doi",
    "url",
]

ColumnWidth = Literal["narrow", "medium", "wide"]


class ColumnSpec(BaseModel):
    """One column in the rendered articles table.

    * ``preset=None`` makes this a custom column — every row gets an empty
      placeholder cell the user fills in by hand after insertion.
    * ``label`` is what the user sees in the column header; preset
      columns still carry their label so the dialog can rename them.
    * ``width_hint`` is rendered as a CSS class on the ``<th>``; pure
      presentation, no business logic depends on it.
    """

    preset: ColumnPreset | None = None
    label: str = Field(min_length=1, max_length=120)
    width_hint: ColumnWidth | None = None


class BuildArticlesTableRequest(BaseModel):
    """POST body for the build-articles-table route."""

    article_ids: list[str] = Field(min_length=1, max_length=200)
    columns: list[ColumnSpec] = Field(min_length=1, max_length=24)
    include_et_al: bool = True
    include_full_authors: bool = False


class BuildArticlesTableResponse(BaseModel):
    html: str
