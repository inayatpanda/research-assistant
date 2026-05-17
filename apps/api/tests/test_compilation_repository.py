import pytest

from research_api.repositories.articles import SqliteArticleRepository
from research_api.repositories.compilation import SqliteCompilationRepository
from research_api.repositories.highlights import SqliteHighlightRepository
from research_api.repositories.projects import SqliteProjectRepository
from research_api.schemas.article import ArticleCreate
from research_api.schemas.highlight import BoundingCoords, BoundingRect, HighlightCreate
from research_api.schemas.project import ProjectCreate


def _coords() -> BoundingCoords:
    return BoundingCoords(rects=[BoundingRect(x0=0.1, y0=0.2, x1=0.4, y1=0.23)])


@pytest.fixture
async def setup(session):
    """Create a project with 2 articles + several highlights of mixed colours."""
    pr = SqliteProjectRepository(session)
    ar = SqliteArticleRepository(session)
    hr = SqliteHighlightRepository(session)

    project = await pr.create(
        ProjectCreate(title="P", study_type="Outcome Study"), user_id="user-a"
    )

    a1 = await ar.create(
        project_id=project.id,
        data=ArticleCreate(
            title="Study One", authors=["Doe", "Smith"], year=2024, journal="J1"
        ),
        user_id="user-a",
    )
    a2 = await ar.create(
        project_id=project.id,
        data=ArticleCreate(
            title="Study Two", authors=["Black", "Brown", "Stone"], year=2023, journal="J2"
        ),
        user_id="user-a",
    )

    # Article 1: 2 results, 1 intro
    await hr.create(
        article_id=a1.id,
        data=HighlightCreate(
            page_number=1, selected_text="r1", colour="results", section="Results",
            bounding_coords=_coords(), sort_order=10,
        ),
        user_id="user-a",
    )
    await hr.create(
        article_id=a1.id,
        data=HighlightCreate(
            page_number=2, selected_text="r2", colour="results", section="Results",
            bounding_coords=_coords(), sort_order=20,
        ),
        user_id="user-a",
    )
    await hr.create(
        article_id=a1.id,
        data=HighlightCreate(
            page_number=1, selected_text="i1", colour="intro", section="Introduction",
            bounding_coords=_coords(), sort_order=10,
        ),
        user_id="user-a",
    )
    # Article 2: 1 results
    await hr.create(
        article_id=a2.id,
        data=HighlightCreate(
            page_number=1, selected_text="r3", colour="results", section="Results",
            bounding_coords=_coords(), sort_order=5,  # sorts first
        ),
        user_id="user-a",
    )

    return {"project_id": project.id, "a1": a1.id, "a2": a2.id}


@pytest.mark.asyncio
async def test_list_cards_filters_by_colour(session, setup):
    repo = SqliteCompilationRepository(session)
    results = await repo.list_cards(setup["project_id"], "results", user_id="user-a")
    assert len(results) == 3
    assert {c.selected_text for c in results} == {"r1", "r2", "r3"}

    intro = await repo.list_cards(setup["project_id"], "intro", user_id="user-a")
    assert len(intro) == 1
    assert intro[0].selected_text == "i1"


@pytest.mark.asyncio
async def test_list_cards_sorts_by_sort_order_then_page(session, setup):
    repo = SqliteCompilationRepository(session)
    cards = await repo.list_cards(setup["project_id"], "results", user_id="user-a")
    # r3 has sort_order=5, r1=10, r2=20 → expected r3, r1, r2
    assert [c.selected_text for c in cards] == ["r3", "r1", "r2"]


@pytest.mark.asyncio
async def test_list_cards_includes_article_metadata_for_citation(session, setup):
    repo = SqliteCompilationRepository(session)
    cards = await repo.list_cards(setup["project_id"], "results", user_id="user-a")
    # First card is r3, from article 2 with authors=Black, Brown, Stone, year=2023
    first = cards[0]
    assert first.article_authors == ["Black", "Brown", "Stone"]
    assert first.article_year == 2023
    assert first.article_title == "Study Two"


@pytest.mark.asyncio
async def test_list_cards_isolates_by_user(session, setup):
    repo = SqliteCompilationRepository(session)
    assert await repo.list_cards(setup["project_id"], "results", user_id="user-b") == []
