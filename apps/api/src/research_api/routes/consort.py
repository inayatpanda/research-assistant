"""Phase 8.7 — CONSORT routes: GET data + SVG, PATCH data, POST push-to-Methodology.

Push registers `consort-flow` against _BLOCK_TAG_BY_CLASS so the existing
replace-by-class helper in routes/reviews.py keeps the Methodology section
idempotent.
"""
from __future__ import annotations

import base64
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..container import Container, get_container
from ..repositories.consort import SqliteConsortRepository
from ..repositories.projects import SqliteProjectRepository
from ..schemas.consort import ConsortData as ConsortPatch, ConsortGetResponse, ConsortRead
from ..schemas.manuscript_section import ManuscriptSectionRead
from ..services.consort.counter import derive_flow
from ..services.consort.svg_renderer import render_consort_svg


router = APIRouter(tags=["consort"])

RCT_STUDY_TYPE = "Randomised Controlled Trial"


async def _session(
    container: Container = Depends(get_container),
) -> AsyncIterator[AsyncSession]:
    async with container.session_factory() as s:
        yield s


def _user_id(container: Container = Depends(get_container)) -> str:
    return container.settings.local_user_id


def _build_response(row) -> ConsortGetResponse:
    flow = derive_flow(row)
    svg = render_consort_svg(flow)
    return ConsortGetResponse(
        data=ConsortRead.model_validate(row),
        warnings=flow.warnings,
        svg_base64=base64.b64encode(svg.encode("utf-8")).decode("ascii"),
    )


@router.get(
    "/projects/{project_id}/consort",
    response_model=ConsortGetResponse,
)
async def get_consort(
    project_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> ConsortGetResponse:
    proj_repo = SqliteProjectRepository(session)
    proj = await proj_repo.get(project_id, user_id)
    if proj is None:
        raise HTTPException(status_code=404, detail="Project not found")
    repo = SqliteConsortRepository(session)
    row = await repo.get_or_create(project_id=project_id, user_id=user_id)
    return _build_response(row)


@router.patch(
    "/projects/{project_id}/consort",
    response_model=ConsortGetResponse,
)
async def patch_consort(
    project_id: str,
    patch: ConsortPatch,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> ConsortGetResponse:
    proj_repo = SqliteProjectRepository(session)
    proj = await proj_repo.get(project_id, user_id)
    if proj is None:
        raise HTTPException(status_code=404, detail="Project not found")
    repo = SqliteConsortRepository(session)
    row = await repo.update(project_id=project_id, user_id=user_id, patch=patch)
    return _build_response(row)


@router.post(
    "/projects/{project_id}/consort/push",
    response_model=ManuscriptSectionRead,
)
async def push_consort(
    project_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> ManuscriptSectionRead:
    # Defer imports so the reviews module is initialised
    from .reviews import _BLOCK_TAG_BY_CLASS, _push_to_section

    proj_repo = SqliteProjectRepository(session)
    proj = await proj_repo.get(project_id, user_id)
    if proj is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if proj.study_type != RCT_STUDY_TYPE:
        raise HTTPException(
            status_code=422,
            detail="CONSORT push is only available for Randomised Controlled Trial projects",
        )

    repo = SqliteConsortRepository(session)
    row = await repo.get_or_create(project_id=project_id, user_id=user_id)
    flow = derive_flow(row)
    svg = render_consort_svg(flow)
    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    html = (
        f'<figure class="consort-flow">'
        f'<img src="data:image/svg+xml;base64,{encoded}" '
        f'alt="CONSORT 2010 flow diagram"/>'
        f'<figcaption>CONSORT 2010 flow diagram.</figcaption>'
        f'</figure>'
    )
    # Sanity: the class hook must be registered in the reviews push table.
    assert "consort-flow" in _BLOCK_TAG_BY_CLASS, "consort-flow hook missing"
    return await _push_to_section(
        session,
        project_id=project_id,
        section_name="Methodology",
        html=html,
        class_hook="consort-flow",
        user_id=user_id,
    )
