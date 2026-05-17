import pytest

from research_api.repositories.articles import SqliteArticleRepository
from research_api.repositories.highlights import SqliteHighlightRepository
from research_api.repositories.projects import SqliteProjectRepository
from research_api.schemas.article import ArticleCreate
from research_api.schemas.highlight import (
    BoundingCoords,
    BoundingRect,
    HighlightCreate,
    HighlightUpdate,
)
from research_api.schemas.project import ProjectCreate


def _coords() -> BoundingCoords:
    return BoundingCoords(rects=[BoundingRect(x0=0.1, y0=0.2, x1=0.4, y1=0.23)])


def _new(**over) -> HighlightCreate:
    base: dict = {
        "page_number": 1,
        "selected_text": "anterior approach showed faster ambulation",
        "colour": "results",
        "section": "Results",
        "bounding_coords": _coords(),
        "user_note": None,
        "sort_order": 0,
    }
    base.update(over)
    return HighlightCreate(**base)


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
async def test_create_and_get(session, article_id):
    repo = SqliteHighlightRepository(session)
    h = await repo.create(article_id=article_id, data=_new(), user_id="user-a")
    assert h.id
    assert h.colour == "results"
    assert h.bounding_coords == {"rects": [{"x0": 0.1, "y0": 0.2, "x1": 0.4, "y1": 0.23}]}
    fetched = await repo.get(h.id, user_id="user-a")
    assert fetched is not None
    assert fetched.id == h.id


@pytest.mark.asyncio
async def test_user_isolation(session, article_id):
    repo = SqliteHighlightRepository(session)
    h = await repo.create(article_id=article_id, data=_new(), user_id="user-a")
    assert await repo.get(h.id, user_id="user-b") is None
    other = await repo.list_for_article(article_id, user_id="user-b")
    assert other == []


@pytest.mark.asyncio
async def test_list_filter_by_colour_and_page(session, article_id):
    repo = SqliteHighlightRepository(session)
    await repo.create(article_id=article_id, data=_new(colour="results", page_number=1), user_id="user-a")
    await repo.create(
        article_id=article_id,
        data=_new(colour="intro", section="Introduction", page_number=1),
        user_id="user-a",
    )
    await repo.create(article_id=article_id, data=_new(colour="results", page_number=2), user_id="user-a")

    all_ = await repo.list_for_article(article_id, user_id="user-a")
    assert len(all_) == 3

    only_results = await repo.list_for_article(article_id, user_id="user-a", colour="results")
    assert len(only_results) == 2

    only_page_1 = await repo.list_for_article(article_id, user_id="user-a", page=1)
    assert len(only_page_1) == 2


@pytest.mark.asyncio
async def test_update_user_note_and_summary(session, article_id):
    repo = SqliteHighlightRepository(session)
    h = await repo.create(article_id=article_id, data=_new(), user_id="user-a")
    updated = await repo.update(
        h.id,
        HighlightUpdate(user_note="my paraphrase", ai_summary="model summary"),
        user_id="user-a",
    )
    assert updated is not None
    assert updated.user_note == "my paraphrase"
    assert updated.ai_summary == "model summary"


@pytest.mark.asyncio
async def test_update_cross_user_returns_none(session, article_id):
    repo = SqliteHighlightRepository(session)
    h = await repo.create(article_id=article_id, data=_new(), user_id="user-a")
    refused = await repo.update(h.id, HighlightUpdate(user_note="hijack"), user_id="user-b")
    assert refused is None


@pytest.mark.asyncio
async def test_delete_scoped(session, article_id):
    repo = SqliteHighlightRepository(session)
    h = await repo.create(article_id=article_id, data=_new(), user_id="user-a")
    await repo.delete(h.id, user_id="user-b")  # wrong user — no-op
    assert await repo.get(h.id, user_id="user-a") is not None
    await repo.delete(h.id, user_id="user-a")
    assert await repo.get(h.id, user_id="user-a") is None
