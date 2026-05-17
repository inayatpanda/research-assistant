import pytest

from research_api.repositories.manuscript_sections import (
    SqliteManuscriptSectionRepository,
)
from research_api.repositories.projects import SqliteProjectRepository
from research_api.schemas.project import ProjectCreate


@pytest.fixture
async def project_id(session):
    p = await SqliteProjectRepository(session).create(
        ProjectCreate(title="P", study_type="Outcome Study"), user_id="user-a"
    )
    return p.id


@pytest.mark.asyncio
async def test_get_returns_none_initially(session, project_id):
    repo = SqliteManuscriptSectionRepository(session)
    assert (
        await repo.get(project_id=project_id, section_name="Results", user_id="user-a")
        is None
    )


@pytest.mark.asyncio
async def test_upsert_creates_and_updates_same_row(session, project_id):
    repo = SqliteManuscriptSectionRepository(session)
    first = await repo.upsert(
        project_id=project_id,
        section_name="Results",
        content="initial draft",
        user_id="user-a",
    )
    assert first.id
    assert first.content == "initial draft"
    assert first.word_count == 2

    second = await repo.upsert(
        project_id=project_id,
        section_name="Results",
        content="updated draft with more words",
        user_id="user-a",
    )
    assert second.id == first.id  # same row
    assert second.content == "updated draft with more words"
    assert second.word_count == 5


@pytest.mark.asyncio
async def test_two_users_have_separate_rows(session, project_id):
    repo = SqliteManuscriptSectionRepository(session)
    a = await repo.upsert(
        project_id=project_id, section_name="Results", content="a-draft", user_id="user-a"
    )
    b = await repo.upsert(
        project_id=project_id, section_name="Results", content="b-draft", user_id="user-b"
    )
    assert a.id != b.id
    assert (
        await repo.get(project_id=project_id, section_name="Results", user_id="user-a")
    ).content == "a-draft"
    assert (
        await repo.get(project_id=project_id, section_name="Results", user_id="user-b")
    ).content == "b-draft"


@pytest.mark.asyncio
async def test_different_sections_in_same_project_are_separate(session, project_id):
    repo = SqliteManuscriptSectionRepository(session)
    a = await repo.upsert(
        project_id=project_id,
        section_name="Introduction",
        content="intro",
        user_id="user-a",
    )
    b = await repo.upsert(
        project_id=project_id,
        section_name="Results",
        content="results",
        user_id="user-a",
    )
    assert a.id != b.id


@pytest.mark.asyncio
async def test_empty_content_allowed(session, project_id):
    repo = SqliteManuscriptSectionRepository(session)
    s = await repo.upsert(
        project_id=project_id, section_name="Results", content="", user_id="user-a"
    )
    assert s.content == ""
    assert s.word_count == 0
