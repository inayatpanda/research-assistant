import pytest

from research_api.repositories.articles import SqliteArticleRepository
from research_api.repositories.notes import SqliteArticleNoteRepository
from research_api.repositories.projects import SqliteProjectRepository
from research_api.schemas.article import ArticleCreate
from research_api.schemas.project import ProjectCreate


@pytest.fixture
async def article_id(session):
    pr = await SqliteProjectRepository(session).create(
        ProjectCreate(title="P", study_type="Outcome Study"), user_id="user-a"
    )
    a = await SqliteArticleRepository(session).create(
        project_id=pr.id, data=ArticleCreate(title="T"), user_id="user-a"
    )
    return a.id


@pytest.mark.asyncio
async def test_get_returns_none_when_no_note(session, article_id):
    repo = SqliteArticleNoteRepository(session)
    assert await repo.get(article_id, user_id="user-a") is None


@pytest.mark.asyncio
async def test_upsert_creates_then_updates(session, article_id):
    repo = SqliteArticleNoteRepository(session)
    first = await repo.upsert(article_id=article_id, content="initial", user_id="user-a")
    assert first.content == "initial"
    first_id = first.id

    second = await repo.upsert(article_id=article_id, content="updated", user_id="user-a")
    assert second.id == first_id  # same row
    assert second.content == "updated"


@pytest.mark.asyncio
async def test_two_users_have_separate_notes(session, article_id):
    repo = SqliteArticleNoteRepository(session)
    a_note = await repo.upsert(article_id=article_id, content="a-note", user_id="user-a")
    b_note = await repo.upsert(article_id=article_id, content="b-note", user_id="user-b")
    assert a_note.id != b_note.id
    fetched_a = await repo.get(article_id, user_id="user-a")
    fetched_b = await repo.get(article_id, user_id="user-b")
    assert fetched_a is not None and fetched_a.content == "a-note"
    assert fetched_b is not None and fetched_b.content == "b-note"


@pytest.mark.asyncio
async def test_empty_content_allowed(session, article_id):
    repo = SqliteArticleNoteRepository(session)
    note = await repo.upsert(article_id=article_id, content="", user_id="user-a")
    assert note.content == ""
