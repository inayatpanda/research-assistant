"""MeSH lookup + suggest routes (Phase 19 / MP19)."""
from __future__ import annotations

import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..container import Container, get_container
from ..repositories.projects import SqliteProjectRepository
from ..repositories.reviews import SqliteReviewRepository
from ..repositories.sr_depth import SqliteMeshTermsRepository
from ..schemas.mesh import (
    MeshSearchHit,
    MeshSearchResponse,
    MeshSuggestRequest,
    MeshTermCreate,
    MeshTermRead,
)
from ..services.ingest.mesh import search_mesh
from ..services.ingest.mesh_suggester import suggest_mesh_from_pico

router = APIRouter(tags=["mesh"])
log = logging.getLogger("research_api.mesh")


async def _session(
    container: Container = Depends(get_container),
) -> AsyncIterator[AsyncSession]:
    async with container.session_factory() as s:
        yield s


def _user_id(container: Container = Depends(get_container)) -> str:
    return container.settings.local_user_id


async def _ensure_project(project_id: str, session: AsyncSession, user_id: str) -> None:
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")


@router.get(
    "/projects/{project_id}/review/mesh/cache",
    response_model=list[MeshTermRead],
)
async def list_cached_mesh(
    project_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> list[MeshTermRead]:
    await _ensure_project(project_id, session, user_id)
    repo = SqliteMeshTermsRepository(session)
    rows = await repo.list_for_project(project_id, user_id)
    return [MeshTermRead.model_validate(r) for r in rows]


@router.post(
    "/projects/{project_id}/review/mesh/cache",
    response_model=MeshTermRead,
    status_code=status.HTTP_201_CREATED,
)
async def upsert_cached_mesh(
    project_id: str,
    body: MeshTermCreate,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> MeshTermRead:
    await _ensure_project(project_id, session, user_id)
    repo = SqliteMeshTermsRepository(session)
    row = await repo.upsert(
        project_id=project_id,
        user_id=user_id,
        descriptor_ui=body.descriptor_ui,
        descriptor_name=body.descriptor_name,
        scope_note=body.scope_note,
        tree_numbers=body.tree_numbers,
        entry_terms=body.entry_terms,
        source=body.source,
    )
    return MeshTermRead.model_validate(row)


@router.delete(
    "/projects/{project_id}/review/mesh/cache/{mesh_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_cached_mesh(
    project_id: str,
    mesh_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> None:
    await _ensure_project(project_id, session, user_id)
    repo = SqliteMeshTermsRepository(session)
    row = await repo.get(mesh_id, user_id)
    if row is None or row.project_id != project_id:
        raise HTTPException(status_code=404, detail="MeSH cache row not found")
    await repo.delete(mesh_id, user_id)
    return None


@router.get(
    "/projects/{project_id}/review/mesh/search",
    response_model=MeshSearchResponse,
)
async def search_mesh_route(
    project_id: str,
    q: str = Query(..., min_length=1, max_length=500),
    retmax: int = Query(default=20, ge=1, le=100),
    cache: bool = Query(default=True),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
    container: Container = Depends(get_container),
) -> MeshSearchResponse:
    await _ensure_project(project_id, session, user_id)
    api_key = getattr(container.settings, "ncbi_api_key", None)
    descriptors = await search_mesh(q, retmax=retmax, api_key=api_key)
    hits = [
        MeshSearchHit(
            descriptor_ui=d.descriptor_ui,
            descriptor_name=d.descriptor_name,
            scope_note=d.scope_note,
            tree_numbers=list(d.tree_numbers),
            entry_terms=list(d.entry_terms),
        )
        for d in descriptors
    ]
    # Best-effort cache fill — failures here mustn't break the search.
    if cache and hits:
        repo = SqliteMeshTermsRepository(session)
        try:
            for d in descriptors:
                await repo.upsert(
                    project_id=project_id,
                    user_id=user_id,
                    descriptor_ui=d.descriptor_ui,
                    descriptor_name=d.descriptor_name,
                    scope_note=d.scope_note,
                    tree_numbers=list(d.tree_numbers),
                    entry_terms=list(d.entry_terms),
                    source="ncbi_lookup",
                )
        except Exception:  # noqa: BLE001 — log and swallow
            log.warning("mesh cache fill failed", exc_info=True)
    return MeshSearchResponse(query=q, hits=hits)


@router.post(
    "/projects/{project_id}/review/mesh/suggest",
    response_model=MeshSearchResponse,
)
async def suggest_mesh_route(
    project_id: str,
    body: MeshSuggestRequest | None = None,
    retmax: int = Query(default=10, ge=1, le=50),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
    container: Container = Depends(get_container),
) -> MeshSearchResponse:
    await _ensure_project(project_id, session, user_id)
    review_repo = SqliteReviewRepository(session)
    review = await review_repo.get_or_create(project_id=project_id, user_id=user_id)
    pico = {
        "population": (body.population if body else None) or review.pico_population,
        "intervention": (body.intervention if body else None) or review.pico_intervention,
        "comparator": (body.comparator if body else None) or review.pico_comparator,
        "outcome": (body.outcome if body else None) or review.pico_outcome,
    }
    api_key = getattr(container.settings, "ncbi_api_key", None)
    descriptors = await suggest_mesh_from_pico(pico, retmax=retmax, api_key=api_key)
    hits = [
        MeshSearchHit(
            descriptor_ui=d.descriptor_ui,
            descriptor_name=d.descriptor_name,
            scope_note=d.scope_note,
            tree_numbers=list(d.tree_numbers),
            entry_terms=list(d.entry_terms),
        )
        for d in descriptors
    ]
    from ..services.ingest.mesh_suggester import compose_pico_term
    return MeshSearchResponse(query=compose_pico_term(pico), hits=hits)
