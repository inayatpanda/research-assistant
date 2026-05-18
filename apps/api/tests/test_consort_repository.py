"""Phase 8.7 — SqliteConsortRepository tests."""
from __future__ import annotations

import pytest

from research_api.db.models import Project, new_id
from research_api.repositories.consort import SqliteConsortRepository
from research_api.schemas.consort import ConsortData as ConsortPatch


async def _project(session, user_id: str = "alice") -> Project:
    p = Project(id=new_id(), user_id=user_id, title="P", study_type="Randomised Controlled Trial")
    session.add(p)
    await session.commit()
    await session.refresh(p)
    return p


@pytest.mark.asyncio
async def test_consort_repo_get_or_create_idempotent_per_project_user(session) -> None:
    proj = await _project(session)
    repo = SqliteConsortRepository(session)
    a = await repo.get_or_create(project_id=proj.id, user_id="alice")
    b = await repo.get_or_create(project_id=proj.id, user_id="alice")
    assert a.id == b.id


@pytest.mark.asyncio
async def test_consort_repo_update_persists_all_fields(session) -> None:
    proj = await _project(session)
    repo = SqliteConsortRepository(session)
    patch = ConsortPatch(
        enrollment_assessed=200,
        enrollment_excluded=50,
        enrollment_excluded_reasons={"Declined": 30, "Ineligible": 20},
        randomised=150,
        allocated_intervention=75,
        allocated_control=75,
    )
    row = await repo.update(project_id=proj.id, user_id="alice", patch=patch)
    assert row.enrollment_assessed == 200
    assert row.randomised == 150
    assert row.enrollment_excluded_reasons == {"Declined": 30, "Ineligible": 20}


@pytest.mark.asyncio
async def test_consort_repo_isolated_per_user(session) -> None:
    proj = await _project(session, user_id="alice")
    repo = SqliteConsortRepository(session)
    await repo.update(
        project_id=proj.id, user_id="alice",
        patch=ConsortPatch(randomised=100),
    )
    # Bob gets his own row for the same project
    bob_row = await repo.get_or_create(project_id=proj.id, user_id="bob")
    assert bob_row.randomised is None
