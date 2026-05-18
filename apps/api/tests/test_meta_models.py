import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from research_api.db.models import (
    Article,
    MetaAnalysis,
    MetaInput,
    Project,
    Review,
)


async def _project(session, user_id: str = "user-a") -> Project:
    p = Project(user_id=user_id, title="P", study_type="Systematic Review")
    session.add(p)
    await session.flush()
    return p


async def _article(session, project: Project, title: str = "A title") -> Article:
    a = Article(
        user_id=project.user_id,
        project_id=project.id,
        title=title,
        authors=["Smith J"],
        year=2024,
    )
    session.add(a)
    await session.flush()
    return a


@pytest.mark.asyncio
async def test_meta_analysis_round_trip(session):
    p = await _project(session)
    r = Review(user_id="user-a", project_id=p.id)
    session.add(r)
    await session.flush()

    m = MetaAnalysis(
        user_id="user-a",
        review_id=r.id,
        title="Pain at 6 weeks",
        effect_metric="smd",
        model="random",
    )
    session.add(m)
    await session.flush()

    row = (
        await session.execute(select(MetaAnalysis).where(MetaAnalysis.id == m.id))
    ).scalar_one()
    assert row.effect_metric == "smd"
    assert row.model == "random"
    assert row.status == "draft"
    assert row.created_at is not None


@pytest.mark.asyncio
async def test_meta_input_unique_per_meta_article(session):
    p = await _project(session)
    r = Review(user_id="user-a", project_id=p.id)
    session.add(r)
    a = await _article(session, p)
    await session.flush()

    m = MetaAnalysis(
        user_id="user-a", review_id=r.id, effect_metric="md", model="fixed"
    )
    session.add(m)
    await session.flush()

    session.add(MetaInput(
        user_id="user-a", meta_id=m.id, article_id=a.id,
        mean_a=1.0, sd_a=0.5, n_a=20, mean_b=0.5, sd_b=0.5, n_b=20,
    ))
    await session.flush()

    # Same (meta_id, article_id) → UNIQUE violation
    session.add(MetaInput(
        user_id="user-a", meta_id=m.id, article_id=a.id,
        mean_a=2.0, sd_a=0.5, n_a=20, mean_b=0.5, sd_b=0.5, n_b=20,
    ))
    with pytest.raises(IntegrityError):
        await session.flush()


@pytest.mark.asyncio
async def test_meta_input_cascade_delete(session):
    p = await _project(session)
    r = Review(user_id="user-a", project_id=p.id)
    session.add(r)
    a = await _article(session, p)
    await session.flush()

    m = MetaAnalysis(
        user_id="user-a", review_id=r.id, effect_metric="or", model="fixed"
    )
    session.add(m)
    await session.flush()

    inp = MetaInput(
        user_id="user-a", meta_id=m.id, article_id=a.id,
        events_a=10, n_a_total=50, events_b=5, n_b_total=50,
    )
    session.add(inp)
    await session.flush()

    # Pragma FKs are enabled in tests
    from sqlalchemy import delete as sa_delete
    await session.execute(sa_delete(MetaAnalysis).where(MetaAnalysis.id == m.id))
    await session.flush()

    remaining = (
        await session.execute(select(MetaInput).where(MetaInput.meta_id == m.id))
    ).scalars().all()
    assert remaining == []
