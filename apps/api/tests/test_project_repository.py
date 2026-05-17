import pytest

from research_api.repositories.projects import SqliteProjectRepository
from research_api.schemas.project import ProjectCreate, ProjectUpdate


@pytest.mark.asyncio
async def test_create_and_get(session):
    repo = SqliteProjectRepository(session)
    created = await repo.create(
        ProjectCreate(title="My Study", study_type="Outcome Study"),
        user_id="user-a",
    )
    assert created.id
    assert created.user_id == "user-a"
    assert created.title == "My Study"
    assert created.citation_style == "vancouver"

    fetched = await repo.get(created.id, user_id="user-a")
    assert fetched is not None
    assert fetched.id == created.id


@pytest.mark.asyncio
async def test_get_rejects_other_user(session):
    repo = SqliteProjectRepository(session)
    created = await repo.create(
        ProjectCreate(title="Owned", study_type="Group Comparison"),
        user_id="user-a",
    )
    assert await repo.get(created.id, user_id="user-b") is None


@pytest.mark.asyncio
async def test_list_for_user_only_returns_owned(session):
    repo = SqliteProjectRepository(session)
    await repo.create(ProjectCreate(title="A", study_type="Outcome Study"), user_id="user-a")
    await repo.create(ProjectCreate(title="B", study_type="Outcome Study"), user_id="user-a")
    await repo.create(ProjectCreate(title="C", study_type="Outcome Study"), user_id="user-b")
    user_a_projects = await repo.list_for_user("user-a")
    assert len(user_a_projects) == 2
    assert {p.title for p in user_a_projects} == {"A", "B"}


@pytest.mark.asyncio
async def test_update_scoped_to_user(session):
    repo = SqliteProjectRepository(session)
    created = await repo.create(
        ProjectCreate(title="Old", study_type="Outcome Study"),
        user_id="user-a",
    )
    updated = await repo.update(created.id, ProjectUpdate(title="New"), user_id="user-a")
    assert updated is not None
    assert updated.title == "New"

    # Wrong user cannot update
    refused = await repo.update(created.id, ProjectUpdate(title="Hijack"), user_id="user-b")
    assert refused is None
    confirmed = await repo.get(created.id, user_id="user-a")
    assert confirmed.title == "New"  # unchanged by user-b


@pytest.mark.asyncio
async def test_delete_scoped_to_user(session):
    repo = SqliteProjectRepository(session)
    created = await repo.create(
        ProjectCreate(title="X", study_type="Outcome Study"),
        user_id="user-a",
    )
    # Wrong user deletes nothing
    await repo.delete(created.id, user_id="user-b")
    still_there = await repo.get(created.id, user_id="user-a")
    assert still_there is not None

    # Owner deletes successfully
    await repo.delete(created.id, user_id="user-a")
    assert await repo.get(created.id, user_id="user-a") is None
