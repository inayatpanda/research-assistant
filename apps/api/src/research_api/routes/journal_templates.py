"""Phase 8.7 — Journal templates: public GET catalogue endpoint."""
from __future__ import annotations

from fastapi import APIRouter

from ..schemas.journal_template import JournalTemplate
from ..services.journal_templates.catalogue import list_templates


router = APIRouter(tags=["journal-templates"])


@router.get("/journal-templates", response_model=list[JournalTemplate])
async def list_journal_templates() -> list[JournalTemplate]:
    return list_templates()
