"""Phase 20 (MP20) — Reporting-checklist Pydantic schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


ChecklistItemStatus = Literal["pass", "fail", "unclear", "na"]


class ChecklistCatalogueItem(BaseModel):
    id: str
    title: str
    description: str
    section_hint: str


class ChecklistCatalogueRead(BaseModel):
    key: str
    name: str
    description: str
    version: str
    default_section: str
    items: list[ChecklistCatalogueItem]


class ChecklistCatalogueSummary(BaseModel):
    key: str
    name: str
    description: str
    version: str
    default_section: str
    item_count: int


class ChecklistRunItem(BaseModel):
    item_id: str
    item_text: str
    status: ChecklistItemStatus = "unclear"
    comment: str = ""
    mapped_section: str | None = None
    mapped_text_excerpt: str | None = None


class ChecklistRunCreate(BaseModel):
    checklist_key: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=255)


class ChecklistRunItemPatch(BaseModel):
    status: ChecklistItemStatus | None = None
    comment: str | None = None
    mapped_section: str | None = None
    mapped_text_excerpt: str | None = None


class ChecklistRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    checklist_key: str
    title: str
    items: list[ChecklistRunItem]
    overall_compliance_pct: float
    created_at: datetime
    updated_at: datetime


class ChecklistRunSummary(BaseModel):
    """Lightweight list-view row (omits items array)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    checklist_key: str
    title: str
    overall_compliance_pct: float
    item_count: int
    created_at: datetime
    updated_at: datetime
