import pytest
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from research_api.db.models import (
    Article,
    ExtractionRecord,
    Project,
    Review,
    RobAssessment,
    ScreeningRecord,
    SearchRecord,
)


async def _project(session, user_id: str = "user-a") -> Project:
    p = Project(user_id=user_id, title="P", study_type="Systematic Review")
    session.add(p)
    await session.flush()
    return p


async def _article(session, project: Project) -> Article:
    a = Article(
        user_id=project.user_id,
        project_id=project.id,
        title="A title",
        authors=["Smith J"],
        year=2024,
    )
    session.add(a)
    await session.flush()
    return a


@pytest.mark.asyncio
async def test_review_round_trip_and_one_per_project(session):
    p = await _project(session)
    r = Review(
        user_id="user-a",
        project_id=p.id,
        pico_population="adults with osteoarthritis",
        eligibility_inclusion="RCTs only",
    )
    session.add(r)
    await session.flush()

    row = (await session.execute(select(Review).where(Review.id == r.id))).scalar_one()
    assert row.pico_population == "adults with osteoarthritis"
    assert row.created_at is not None

    # Second review on the same project for the same user → UNIQUE violation
    dup = Review(user_id="user-a", project_id=p.id)
    session.add(dup)
    with pytest.raises(IntegrityError):
        await session.flush()


@pytest.mark.asyncio
async def test_search_record_round_trip(session):
    p = await _project(session)
    r = Review(user_id="user-a", project_id=p.id)
    session.add(r)
    await session.flush()

    s = SearchRecord(
        user_id="user-a",
        review_id=r.id,
        database_name="PubMed",
        query_string="hip arthroplasty AND outcomes",
        date_searched=datetime(2024, 6, 1),
        n_results=412,
    )
    session.add(s)
    await session.flush()

    row = (await session.execute(select(SearchRecord).where(SearchRecord.id == s.id))).scalar_one()
    assert row.database_name == "PubMed"
    assert row.n_results == 412


@pytest.mark.asyncio
async def test_screening_record_unique_per_article_stage(session):
    p = await _project(session)
    r = Review(user_id="user-a", project_id=p.id)
    session.add(r)
    a = await _article(session, p)
    await session.flush()

    session.add(ScreeningRecord(
        user_id="user-a", review_id=r.id, article_id=a.id,
        stage="title_abstract", decision="include",
    ))
    await session.flush()

    # Same (review, article, stage) → UNIQUE violation
    session.add(ScreeningRecord(
        user_id="user-a", review_id=r.id, article_id=a.id,
        stage="title_abstract", decision="exclude",
    ))
    with pytest.raises(IntegrityError):
        await session.flush()


@pytest.mark.asyncio
async def test_screening_record_distinct_stages_allowed(session):
    p = await _project(session)
    r = Review(user_id="user-a", project_id=p.id)
    session.add(r)
    a = await _article(session, p)
    await session.flush()

    session.add(ScreeningRecord(
        user_id="user-a", review_id=r.id, article_id=a.id,
        stage="title_abstract", decision="include",
    ))
    session.add(ScreeningRecord(
        user_id="user-a", review_id=r.id, article_id=a.id,
        stage="full_text", decision="include",
    ))
    await session.flush()


@pytest.mark.asyncio
async def test_rob_assessment_unique_per_tool(session):
    p = await _project(session)
    r = Review(user_id="user-a", project_id=p.id)
    session.add(r)
    a = await _article(session, p)
    await session.flush()

    session.add(RobAssessment(
        user_id="user-a", review_id=r.id, article_id=a.id, tool="rob2",
        domain_answers={"D1": "low"}, overall_auto="low",
    ))
    await session.flush()

    session.add(RobAssessment(
        user_id="user-a", review_id=r.id, article_id=a.id, tool="rob2",
        domain_answers={"D1": "high"}, overall_auto="high",
    ))
    with pytest.raises(IntegrityError):
        await session.flush()


@pytest.mark.asyncio
async def test_extraction_record_unique_per_article(session):
    p = await _project(session)
    r = Review(user_id="user-a", project_id=p.id)
    session.add(r)
    a = await _article(session, p)
    await session.flush()

    session.add(ExtractionRecord(
        user_id="user-a", review_id=r.id, article_id=a.id,
        fields={"design": "RCT", "n": 120},
    ))
    await session.flush()

    session.add(ExtractionRecord(
        user_id="user-a", review_id=r.id, article_id=a.id,
        fields={"design": "cohort"},
    ))
    with pytest.raises(IntegrityError):
        await session.flush()


@pytest.mark.asyncio
async def test_articles_abstract_column_persists(session):
    p = await _project(session)
    a = Article(
        user_id="user-a", project_id=p.id,
        title="T", authors=["X"], abstract="Background: ...",
    )
    session.add(a)
    await session.flush()
    row = (await session.execute(select(Article).where(Article.id == a.id))).scalar_one()
    assert row.abstract == "Background: ..."
