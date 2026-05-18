"""Phase 11 — manuscript snapshot Pydantic schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SnapshotCreate(BaseModel):
    label: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)


class SnapshotSummary(BaseModel):
    """Lightweight row used in list responses — `full_blob` omitted."""

    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    label: str
    description: str | None
    created_at: datetime


class SnapshotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    label: str
    description: str | None
    full_blob: dict[str, Any]
    created_at: datetime


# ── Diff payload ─────────────────────────────────────────────────────


class DiffLine(BaseModel):
    """One unified-diff line.

    `type` is one of:
      "+" — addition in the right-hand (newer) side
      "-" — deletion (only in left-hand)
      "=" — unchanged context line
    """

    type: str = Field(min_length=1, max_length=1)
    line: str


class SectionDiff(BaseModel):
    """Per-section unified diff payload."""

    section_name: str
    lines: list[DiffLine]


class SnapshotDiffResponse(BaseModel):
    """Diff between two snapshots (or one snapshot vs. current state).

    `sections` is keyed by section_name; each value is the line-by-line
    unified diff produced by `difflib.unified_diff` then post-processed
    into `+ / - / =` markers. Empty list for sections with no changes.
    """

    base_snapshot_id: str
    target_snapshot_id: str | None  # null when comparing against current
    sections: dict[str, list[DiffLine]]
