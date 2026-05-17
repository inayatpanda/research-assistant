import pytest

from research_api.repositories.articles import SqliteArticleRepository
from research_api.repositories.projects import SqliteProjectRepository
from research_api.schemas.article import ArticleCreate, ArticleFilters, ArticleUpdate
from research_api.schemas.project import ProjectCreate


@pytest.fixture
async def project_id(session):
    repo = SqliteProjectRepository(session)
    proj = await repo.create(
        ProjectCreate(title="P", study_type="Outcome Study"), user_id="user-a"
    )
    return proj.id


@pytest.mark.asyncio
async def test_create_and_get(session, project_id):
    repo = SqliteArticleRepository(session)
    created = await repo.create(
        project_id=project_id,
        data=ArticleCreate(
            title="Hip RCT",
            authors=["Jane Doe"],
            journal="JBJS",
            year=2024,
            doi="10.1/abc",
        ),
        user_id="user-a",
    )
    assert created.id
    assert created.user_id == "user-a"
    assert created.title == "Hip RCT"
    assert created.review_status == "pending"

    fetched = await repo.get(created.id, user_id="user-a")
    assert fetched is not None
    assert fetched.id == created.id


@pytest.mark.asyncio
async def test_user_isolation(session, project_id):
    repo = SqliteArticleRepository(session)
    a = await repo.create(
        project_id=project_id,
        data=ArticleCreate(title="X"),
        user_id="user-a",
    )
    assert await repo.get(a.id, user_id="user-b") is None
    other_list = await repo.list_for_project(project_id, user_id="user-b", filters=ArticleFilters())
    assert other_list == []


@pytest.mark.asyncio
async def test_list_filter_search_sort(session, project_id):
    repo = SqliteArticleRepository(session)
    await repo.create(
        project_id=project_id,
        data=ArticleCreate(title="Anterior approach hip", year=2020, study_design="RCT"),
        user_id="user-a",
    )
    await repo.create(
        project_id=project_id,
        data=ArticleCreate(title="Posterior approach hip", year=2022, study_design="cohort"),
        user_id="user-a",
    )
    await repo.create(
        project_id=project_id,
        data=ArticleCreate(title="Knee outcomes", year=2024, review_status="excluded"),
        user_id="user-a",
    )

    # Search
    hits = await repo.list_for_project(
        project_id, user_id="user-a", filters=ArticleFilters(q="approach")
    )
    assert len(hits) == 2

    # Filter by study design
    rcts = await repo.list_for_project(
        project_id, user_id="user-a", filters=ArticleFilters(study_design="RCT")
    )
    assert len(rcts) == 1
    assert rcts[0].title == "Anterior approach hip"

    # Filter by review status
    excluded = await repo.list_for_project(
        project_id, user_id="user-a", filters=ArticleFilters(review_status="excluded")
    )
    assert len(excluded) == 1

    # Sort by year desc (default for non-created_desc not tested here; pick year_desc explicitly)
    sorted_year_desc = await repo.list_for_project(
        project_id, user_id="user-a", filters=ArticleFilters(sort="year_desc")
    )
    assert [a.year for a in sorted_year_desc] == [2024, 2022, 2020]


@pytest.mark.asyncio
async def test_find_duplicate_by_doi(session, project_id):
    repo = SqliteArticleRepository(session)
    await repo.create(
        project_id=project_id,
        data=ArticleCreate(title="Whatever", doi="10.1/abc"),
        user_id="user-a",
    )
    dup = await repo.find_duplicate(
        project_id=project_id, doi="10.1/abc", title="Different title", user_id="user-a"
    )
    assert dup is not None
    assert dup.doi == "10.1/abc"


@pytest.mark.asyncio
async def test_find_duplicate_by_title_fuzz(session, project_id):
    repo = SqliteArticleRepository(session)
    await repo.create(
        project_id=project_id,
        data=ArticleCreate(title="Anterior approach in total hip arthroplasty"),
        user_id="user-a",
    )
    dup = await repo.find_duplicate(
        project_id=project_id,
        doi=None,
        title="anterior approach in TOTAL hip arthroplasty",
        user_id="user-a",
    )
    assert dup is not None


@pytest.mark.asyncio
async def test_find_duplicate_returns_none_when_unrelated(session, project_id):
    repo = SqliteArticleRepository(session)
    await repo.create(
        project_id=project_id,
        data=ArticleCreate(title="Anterior approach hip"),
        user_id="user-a",
    )
    dup = await repo.find_duplicate(
        project_id=project_id,
        doi=None,
        title="Knee meniscus tear treatment",
        user_id="user-a",
    )
    assert dup is None


@pytest.mark.asyncio
async def test_find_duplicate_with_multiple_existing_dois(session, project_id):
    """Regression: when 2+ existing rows share a DOI, find_duplicate must return one,
    not raise MultipleResultsFound."""
    repo = SqliteArticleRepository(session)
    await repo.create(
        project_id=project_id,
        data=ArticleCreate(title="First", doi="10.1/dup"),
        user_id="user-a",
    )
    await repo.create(
        project_id=project_id,
        data=ArticleCreate(title="Second", doi="10.1/dup"),
        user_id="user-a",
    )
    dup = await repo.find_duplicate(
        project_id=project_id, doi="10.1/dup", title="Whatever", user_id="user-a"
    )
    assert dup is not None
    assert dup.doi == "10.1/dup"


@pytest.mark.asyncio
async def test_find_duplicate_scoped_to_user(session, project_id):
    """User A's article must not match against User B's lookup."""
    repo = SqliteArticleRepository(session)
    await repo.create(
        project_id=project_id,
        data=ArticleCreate(title="Hip outcomes", doi="10.1/shared"),
        user_id="user-a",
    )
    # User B uploads the same DOI in their own project — should NOT see user-a's article as duplicate.
    proj_repo = SqliteProjectRepository(session)
    b_proj = await proj_repo.create(
        ProjectCreate(title="B's Project", study_type="Outcome Study"), user_id="user-b"
    )
    dup = await repo.find_duplicate(
        project_id=b_proj.id, doi="10.1/shared", title="Hip outcomes", user_id="user-b"
    )
    assert dup is None


@pytest.mark.asyncio
async def test_update_and_delete_scoped(session, project_id):
    repo = SqliteArticleRepository(session)
    a = await repo.create(
        project_id=project_id, data=ArticleCreate(title="Old"), user_id="user-a"
    )
    updated = await repo.update(a.id, ArticleUpdate(title="New"), user_id="user-a")
    assert updated is not None
    assert updated.title == "New"

    refused = await repo.update(a.id, ArticleUpdate(title="Hijack"), user_id="user-b")
    assert refused is None

    # Delete by wrong user is a no-op
    await repo.delete(a.id, user_id="user-b")
    assert await repo.get(a.id, user_id="user-a") is not None
    # Owner deletes
    await repo.delete(a.id, user_id="user-a")
    assert await repo.get(a.id, user_id="user-a") is None
