"""Phase 20 (MP20) — Interactive reporting-checklist routes.

Endpoints (all under ``/api`` via the mounted router prefix):

  GET    /checklists/catalogue                 metadata list
  GET    /checklists/catalogue/{key}           full catalogue with items
  GET    /projects/{pid}/checklists            list runs
  POST   /projects/{pid}/checklists            create a fresh run
  GET    /projects/{pid}/checklists/{run_id}   read one
  PATCH  /projects/{pid}/checklists/{run_id}/items/{item_id}  patch one item
  POST   /projects/{pid}/checklists/{run_id}/auto-check       best-effort prefill
  POST   /projects/{pid}/checklists/{run_id}/export?format=pdf|docx
  DELETE /projects/{pid}/checklists/{run_id}
"""
from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from ..container import Container, get_container
from ..auth_deps import get_current_user
from ..schemas.auth import UserRead
from ..repositories.checklists import SqliteChecklistRepository
from ..repositories.manuscript_sections import SqliteManuscriptSectionRepository
from ..repositories.projects import SqliteProjectRepository
from ..schemas.checklists import (
    ChecklistCatalogueRead,
    ChecklistCatalogueSummary,
    ChecklistRunCreate,
    ChecklistRunItemPatch,
    ChecklistRunRead,
    ChecklistRunSummary,
)
from ..services.checklists.auto_check import auto_check, initial_items
from ..services.checklists.catalogue import (
    get_catalogue,
    list_catalogues,
)
from ..services.checklists.export import render_docx, render_pdf


router = APIRouter(tags=["checklists"])


async def _session(
    container: Container = Depends(get_container),
) -> AsyncIterator[AsyncSession]:
    async with container.session_factory() as s:
        yield s


def _user_id(user: UserRead = Depends(get_current_user)) -> str:
    # Phase S1 — delegate to the real session-derived user. The legacy
    # static-id flow remains available via ``RMA_DISABLE_AUTH=1``.
    return user.id


async def _ensure_project(
    project_id: str, session: AsyncSession, user_id: str
) -> None:
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")


def _to_summary(row) -> ChecklistRunSummary:
    items = list(row.items or [])
    return ChecklistRunSummary(
        id=row.id,
        project_id=row.project_id,
        checklist_key=row.checklist_key,
        title=row.title,
        overall_compliance_pct=row.overall_compliance_pct,
        item_count=len(items),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


# ── Catalogue endpoints ──────────────────────────────────────────────────


@router.get(
    "/checklists/catalogue",
    response_model=list[ChecklistCatalogueSummary],
)
async def list_catalogue() -> list[ChecklistCatalogueSummary]:
    return [ChecklistCatalogueSummary(**c) for c in list_catalogues()]


@router.get(
    "/checklists/catalogue/{key}",
    response_model=ChecklistCatalogueRead,
)
async def get_one_catalogue(key: str) -> ChecklistCatalogueRead:
    cat = get_catalogue(key)
    if cat is None:
        raise HTTPException(status_code=404, detail="Checklist not found")
    return ChecklistCatalogueRead(
        key=cat.key,
        name=cat.name,
        description=cat.description,
        version=cat.version,
        default_section=cat.default_section,
        items=[
            {
                "id": it.id,
                "title": it.title,
                "description": it.description,
                "section_hint": it.section_hint,
            }
            for it in cat.items
        ],
    )


# ── Run endpoints ────────────────────────────────────────────────────────


@router.get(
    "/projects/{project_id}/checklists",
    response_model=list[ChecklistRunSummary],
)
async def list_runs(
    project_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> list[ChecklistRunSummary]:
    await _ensure_project(project_id, session, user_id)
    repo = SqliteChecklistRepository(session)
    rows = await repo.list_for_project(project_id, user_id)
    return [_to_summary(r) for r in rows]


@router.post(
    "/projects/{project_id}/checklists",
    response_model=ChecklistRunRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_run(
    project_id: str,
    body: ChecklistRunCreate,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> ChecklistRunRead:
    await _ensure_project(project_id, session, user_id)
    cat = get_catalogue(body.checklist_key)
    if cat is None:
        raise HTTPException(status_code=404, detail="Checklist not found")
    repo = SqliteChecklistRepository(session)
    row = await repo.create(
        project_id=project_id,
        user_id=user_id,
        checklist_key=cat.key,
        title=body.title,
        items=initial_items(cat),
    )
    if row is None:
        raise HTTPException(
            status_code=409,
            detail="A run with this checklist and title already exists",
        )
    return ChecklistRunRead.model_validate(row)


@router.get(
    "/projects/{project_id}/checklists/{run_id}",
    response_model=ChecklistRunRead,
)
async def get_run(
    project_id: str,
    run_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> ChecklistRunRead:
    await _ensure_project(project_id, session, user_id)
    repo = SqliteChecklistRepository(session)
    row = await repo.get(run_id, user_id)
    if row is None or row.project_id != project_id:
        raise HTTPException(status_code=404, detail="Checklist run not found")
    return ChecklistRunRead.model_validate(row)


@router.patch(
    "/projects/{project_id}/checklists/{run_id}/items/{item_id}",
    response_model=ChecklistRunRead,
)
async def patch_item(
    project_id: str,
    run_id: str,
    item_id: str,
    body: ChecklistRunItemPatch,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> ChecklistRunRead:
    await _ensure_project(project_id, session, user_id)
    repo = SqliteChecklistRepository(session)
    existing = await repo.get(run_id, user_id)
    if existing is None or existing.project_id != project_id:
        raise HTTPException(status_code=404, detail="Checklist run not found")
    patch = body.model_dump(exclude_unset=True)
    row = await repo.patch_item(
        run_id=run_id, user_id=user_id, item_id=item_id, patch=patch
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return ChecklistRunRead.model_validate(row)


@router.post(
    "/projects/{project_id}/checklists/{run_id}/auto-check",
    response_model=ChecklistRunRead,
)
async def run_auto_check(
    project_id: str,
    run_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> ChecklistRunRead:
    await _ensure_project(project_id, session, user_id)
    repo = SqliteChecklistRepository(session)
    existing = await repo.get(run_id, user_id)
    if existing is None or existing.project_id != project_id:
        raise HTTPException(status_code=404, detail="Checklist run not found")
    cat = get_catalogue(existing.checklist_key)
    if cat is None:
        raise HTTPException(status_code=404, detail="Checklist catalogue not found")
    ms_repo = SqliteManuscriptSectionRepository(session)
    sections = await ms_repo.list_for_project(project_id, user_id)
    sections_text = {s.section_name: s.content or "" for s in sections}
    new_items = auto_check(
        catalogue=cat,
        sections_text=sections_text,
        current_items=list(existing.items or []),
    )
    row = await repo.replace_items(
        run_id=run_id, user_id=user_id, items=new_items
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Checklist run not found")
    return ChecklistRunRead.model_validate(row)


@router.post(
    "/projects/{project_id}/checklists/{run_id}/export",
)
async def export_run(
    project_id: str,
    run_id: str,
    format: str = Query("pdf", pattern="^(pdf|docx)$"),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> Response:
    await _ensure_project(project_id, session, user_id)
    repo = SqliteChecklistRepository(session)
    row = await repo.get(run_id, user_id)
    if row is None or row.project_id != project_id:
        raise HTTPException(status_code=404, detail="Checklist run not found")
    cat = get_catalogue(row.checklist_key)
    name = cat.name if cat else row.checklist_key
    items = list(row.items or [])

    if format == "pdf":
        data = render_pdf(
            checklist_name=name,
            run_title=row.title,
            items=items,
            compliance_pct=float(row.overall_compliance_pct),
        )
        return Response(
            content=data,
            media_type="application/pdf",
            headers={
                "Content-Disposition": (
                    f'attachment; filename="checklist-{row.checklist_key}.pdf"'
                ),
            },
        )

    data = render_docx(
        checklist_name=name,
        run_title=row.title,
        items=items,
        compliance_pct=float(row.overall_compliance_pct),
    )
    return Response(
        content=data,
        media_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
        headers={
            "Content-Disposition": (
                f'attachment; filename="checklist-{row.checklist_key}.docx"'
            ),
        },
    )


@router.delete(
    "/projects/{project_id}/checklists/{run_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_run(
    project_id: str,
    run_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> None:
    await _ensure_project(project_id, session, user_id)
    repo = SqliteChecklistRepository(session)
    existing = await repo.get(run_id, user_id)
    if existing is None or existing.project_id != project_id:
        raise HTTPException(status_code=404, detail="Checklist run not found")
    await repo.delete(run_id, user_id)
    return None
