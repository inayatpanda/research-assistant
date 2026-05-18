"""SqliteMetaRepository tests."""
import pytest
from sqlalchemy import select

from research_api.db.models import MetaAnalysis, MetaInput
from research_api.repositories.meta import (
    MetaArticleMismatch,
    SqliteMetaRepository,
)
from research_api.schemas.meta import (
    MetaAnalysisCreate,
    MetaAnalysisUpdate,
    MetaInputCreate,
    MetaInputUpdate,
)
from research_api.services.meta.heterogeneity import Heterogeneity
from research_api.services.meta.pooling import PooledResult
from tests.fixtures.meta_seed import seed_review_with_articles


@pytest.mark.asyncio
async def test_create_meta_with_inputs(session):
    p, r, arts = await seed_review_with_articles(session)
    repo = SqliteMetaRepository(session)
    body = MetaAnalysisCreate(
        title="Test pool",
        effect_metric="md",
        model="fixed",
        inputs=[
            MetaInputCreate(article_id=arts[0].id, mean_a=1.0, sd_a=0.5, n_a=20, mean_b=0.5, sd_b=0.5, n_b=20),
            MetaInputCreate(article_id=arts[1].id, mean_a=2.0, sd_a=0.6, n_a=25, mean_b=1.0, sd_b=0.5, n_b=25),
        ],
    )
    meta = await repo.create(review_id=r.id, data=body, user_id="user-a")
    assert meta.id is not None
    assert meta.user_id == "user-a"
    # Inputs persisted
    inputs = await repo.list_inputs(meta.id, "user-a")
    assert len(inputs) == 2
    assert all(inp.user_id == "user-a" for inp in inputs)


@pytest.mark.asyncio
async def test_get_returns_none_for_wrong_user(session):
    p, r, arts = await seed_review_with_articles(session)
    repo = SqliteMetaRepository(session)
    body = MetaAnalysisCreate(
        effect_metric="md", model="fixed",
        inputs=[
            MetaInputCreate(article_id=arts[0].id, mean_a=1.0, sd_a=0.5, n_a=20, mean_b=0.5, sd_b=0.5, n_b=20),
            MetaInputCreate(article_id=arts[1].id, mean_a=2.0, sd_a=0.6, n_a=25, mean_b=1.0, sd_b=0.5, n_b=25),
        ],
    )
    meta = await repo.create(review_id=r.id, data=body, user_id="user-a")
    assert await repo.get(meta.id, "user-b") is None


@pytest.mark.asyncio
async def test_upsert_input_in_place(session):
    p, r, arts = await seed_review_with_articles(session)
    repo = SqliteMetaRepository(session)
    body = MetaAnalysisCreate(
        effect_metric="md", model="fixed",
        inputs=[
            MetaInputCreate(article_id=arts[0].id, mean_a=1.0, sd_a=0.5, n_a=20, mean_b=0.5, sd_b=0.5, n_b=20),
            MetaInputCreate(article_id=arts[1].id, mean_a=2.0, sd_a=0.6, n_a=25, mean_b=1.0, sd_b=0.5, n_b=25),
        ],
    )
    meta = await repo.create(review_id=r.id, data=body, user_id="user-a")

    # Upsert same article — should overwrite, not create a duplicate row
    upd = MetaInputCreate(
        article_id=arts[0].id, mean_a=99.0, sd_a=0.5, n_a=20, mean_b=0.5, sd_b=0.5, n_b=20,
    )
    await repo.upsert_input(meta_id=meta.id, data=upd, user_id="user-a")
    inputs = await repo.list_inputs(meta.id, "user-a")
    assert len(inputs) == 2  # still 2 rows
    target = [inp for inp in inputs if inp.article_id == arts[0].id][0]
    assert target.mean_a == 99.0


@pytest.mark.asyncio
async def test_write_pooled_persists_numerics(session):
    p, r, arts = await seed_review_with_articles(session)
    repo = SqliteMetaRepository(session)
    body = MetaAnalysisCreate(
        effect_metric="md", model="fixed",
        inputs=[
            MetaInputCreate(article_id=arts[0].id, mean_a=1.0, sd_a=0.5, n_a=20, mean_b=0.5, sd_b=0.5, n_b=20),
            MetaInputCreate(article_id=arts[1].id, mean_a=2.0, sd_a=0.6, n_a=25, mean_b=1.0, sd_b=0.5, n_b=25),
        ],
    )
    meta = await repo.create(review_id=r.id, data=body, user_id="user-a")

    pooled = PooledResult(
        estimate=0.6, se=0.1, ci_low=0.4, ci_high=0.8,
        z=6.0, p=0.0001, weights=[0.5, 0.5], model="fixed",
    )
    het = Heterogeneity(q=0.3, df=1, p=0.58, i2=0.0, tau2=0.0)
    await repo.write_pooled(
        meta_id=meta.id, user_id="user-a",
        pooled=pooled, heterogeneity=het, subgroup_summary=None,
    )
    fresh = await repo.get(meta.id, "user-a")
    assert fresh.pooled_estimate == pytest.approx(0.6)
    assert fresh.q_value == pytest.approx(0.3)
    assert fresh.i2 == pytest.approx(0.0)
    assert fresh.status == "completed"


@pytest.mark.asyncio
async def test_write_interpretation_leaves_numerics(session):
    p, r, arts = await seed_review_with_articles(session)
    repo = SqliteMetaRepository(session)
    body = MetaAnalysisCreate(
        effect_metric="md", model="fixed",
        inputs=[
            MetaInputCreate(article_id=arts[0].id, mean_a=1.0, sd_a=0.5, n_a=20, mean_b=0.5, sd_b=0.5, n_b=20),
            MetaInputCreate(article_id=arts[1].id, mean_a=2.0, sd_a=0.6, n_a=25, mean_b=1.0, sd_b=0.5, n_b=25),
        ],
    )
    meta = await repo.create(review_id=r.id, data=body, user_id="user-a")
    pooled = PooledResult(estimate=0.6, se=0.1, ci_low=0.4, ci_high=0.8, z=6.0, p=0.0001, weights=[0.5, 0.5], model="fixed")
    het = Heterogeneity(q=0.3, df=1, p=0.58, i2=0.0, tau2=0.0)
    await repo.write_pooled(
        meta_id=meta.id, user_id="user-a", pooled=pooled, heterogeneity=het, subgroup_summary=None,
    )
    await repo.write_interpretation(meta_id=meta.id, user_id="user-a", prose="The pooled MD was 0.60.")
    fresh = await repo.get(meta.id, "user-a")
    assert fresh.ai_interpretation == "The pooled MD was 0.60."
    assert fresh.pooled_estimate == pytest.approx(0.6)


@pytest.mark.asyncio
async def test_delete_cascades_inputs(session):
    p, r, arts = await seed_review_with_articles(session)
    repo = SqliteMetaRepository(session)
    body = MetaAnalysisCreate(
        effect_metric="md", model="fixed",
        inputs=[
            MetaInputCreate(article_id=arts[0].id, mean_a=1.0, sd_a=0.5, n_a=20, mean_b=0.5, sd_b=0.5, n_b=20),
            MetaInputCreate(article_id=arts[1].id, mean_a=2.0, sd_a=0.6, n_a=25, mean_b=1.0, sd_b=0.5, n_b=25),
        ],
    )
    meta = await repo.create(review_id=r.id, data=body, user_id="user-a")
    ok = await repo.delete(meta.id, "user-a")
    assert ok is True

    remaining_inputs = (await session.execute(select(MetaInput).where(MetaInput.meta_id == meta.id))).scalars().all()
    assert remaining_inputs == []
    remaining_meta = (await session.execute(select(MetaAnalysis).where(MetaAnalysis.id == meta.id))).scalar_one_or_none()
    assert remaining_meta is None


@pytest.mark.asyncio
async def test_upsert_input_rejects_cross_project_article(session):
    p, r, arts = await seed_review_with_articles(session)
    # Make a second project + article with the same user
    from research_api.db.models import Article, Project
    p2 = Project(user_id="user-a", title="P2", study_type="Systematic Review")
    session.add(p2)
    await session.flush()
    a2 = Article(user_id="user-a", project_id=p2.id, title="Other-project article", authors=["X"], year=2024)
    session.add(a2)
    await session.flush()

    repo = SqliteMetaRepository(session)
    body = MetaAnalysisCreate(
        effect_metric="md", model="fixed",
        inputs=[
            MetaInputCreate(article_id=arts[0].id, mean_a=1.0, sd_a=0.5, n_a=20, mean_b=0.5, sd_b=0.5, n_b=20),
            MetaInputCreate(article_id=arts[1].id, mean_a=2.0, sd_a=0.6, n_a=25, mean_b=1.0, sd_b=0.5, n_b=25),
        ],
    )
    meta = await repo.create(review_id=r.id, data=body, user_id="user-a")

    bogus = MetaInputCreate(article_id=a2.id, mean_a=1.0, sd_a=0.5, n_a=20, mean_b=0.5, sd_b=0.5, n_b=20)
    with pytest.raises(MetaArticleMismatch):
        await repo.upsert_input(meta_id=meta.id, data=bogus, user_id="user-a")


@pytest.mark.asyncio
async def test_update_meta_patch(session):
    p, r, arts = await seed_review_with_articles(session)
    repo = SqliteMetaRepository(session)
    body = MetaAnalysisCreate(
        effect_metric="md", model="fixed",
        inputs=[
            MetaInputCreate(article_id=arts[0].id, mean_a=1.0, sd_a=0.5, n_a=20, mean_b=0.5, sd_b=0.5, n_b=20),
            MetaInputCreate(article_id=arts[1].id, mean_a=2.0, sd_a=0.6, n_a=25, mean_b=1.0, sd_b=0.5, n_b=25),
        ],
    )
    meta = await repo.create(review_id=r.id, data=body, user_id="user-a")
    updated = await repo.update(meta.id, MetaAnalysisUpdate(title="New title"), "user-a")
    assert updated.title == "New title"


@pytest.mark.asyncio
async def test_list_filters_by_review(session):
    p, r, arts = await seed_review_with_articles(session)
    repo = SqliteMetaRepository(session)
    body = MetaAnalysisCreate(
        effect_metric="md", model="fixed",
        inputs=[
            MetaInputCreate(article_id=arts[0].id, mean_a=1.0, sd_a=0.5, n_a=20, mean_b=0.5, sd_b=0.5, n_b=20),
            MetaInputCreate(article_id=arts[1].id, mean_a=2.0, sd_a=0.6, n_a=25, mean_b=1.0, sd_b=0.5, n_b=25),
        ],
    )
    await repo.create(review_id=r.id, data=body, user_id="user-a")
    lst = await repo.list(review_id=r.id, user_id="user-a")
    assert len(lst) == 1
    # Different review id → empty
    lst_b = await repo.list(review_id="nonexistent", user_id="user-a")
    assert lst_b == []
