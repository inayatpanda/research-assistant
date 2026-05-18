"""Phase 8.6 — SqliteArticleRepository.merge() FK rewiring."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from research_api.db.models import (
    Article,
    ArticleNote,
    ExtractionRecord,
    Highlight,
    MetaAnalysis,
    MetaInput,
    Project,
    Review,
    RobAssessment,
    ScreeningRecord,
    new_id,
)
from research_api.repositories.articles import SqliteArticleRepository


async def _seed_project(session: AsyncSession, *, user_id: str = "u1") -> str:
    p = Project(
        id=new_id(),
        user_id=user_id,
        title="P",
        study_type="rct",
    )
    session.add(p)
    await session.commit()
    return p.id


async def _seed_article(
    session: AsyncSession, *, pid: str, user_id: str = "u1", title: str = "T"
) -> str:
    a = Article(
        id=new_id(),
        user_id=user_id,
        project_id=pid,
        title=title,
        source="upload",
    )
    session.add(a)
    await session.commit()
    return a.id


async def _seed_review(
    session: AsyncSession, *, pid: str, user_id: str = "u1"
) -> str:
    r = Review(
        id=new_id(),
        user_id=user_id,
        project_id=pid,
    )
    session.add(r)
    await session.commit()
    return r.id


@pytest.mark.asyncio
async def test_merge_rewrites_highlight_fks(session: AsyncSession):
    pid = await _seed_project(session)
    keep_id = await _seed_article(session, pid=pid)
    drop_id = await _seed_article(session, pid=pid, title="Drop")
    h = Highlight(
        id=new_id(),
        user_id="u1",
        article_id=drop_id,
        page_number=1,
        selected_text="x",
        colour="results",
        section="results",
        bounding_coords={},
    )
    session.add(h)
    await session.commit()

    repo = SqliteArticleRepository(session)
    kept = await repo.merge(keep_id=keep_id, drop_ids=[drop_id], user_id="u1")

    assert kept.id == keep_id
    await session.refresh(h)
    assert h.article_id == keep_id


@pytest.mark.asyncio
async def test_merge_rewrites_article_note_fk_when_no_collision(
    session: AsyncSession,
):
    pid = await _seed_project(session)
    keep_id = await _seed_article(session, pid=pid)
    drop_id = await _seed_article(session, pid=pid, title="Drop")
    n = ArticleNote(
        id=new_id(),
        user_id="u1",
        article_id=drop_id,
        content="my notes",
    )
    session.add(n)
    await session.commit()

    repo = SqliteArticleRepository(session)
    await repo.merge(keep_id=keep_id, drop_ids=[drop_id], user_id="u1")

    await session.refresh(n)
    assert n.article_id == keep_id
    assert n.content == "my notes"


@pytest.mark.asyncio
async def test_merge_deletes_drop_article_note_when_keep_already_has_one(
    session: AsyncSession,
):
    """UNIQUE collision — keep row's note wins, drop row's note is removed."""
    pid = await _seed_project(session)
    keep_id = await _seed_article(session, pid=pid)
    drop_id = await _seed_article(session, pid=pid, title="Drop")
    keep_note = ArticleNote(
        id=new_id(), user_id="u1", article_id=keep_id, content="keep"
    )
    drop_note = ArticleNote(
        id=new_id(), user_id="u1", article_id=drop_id, content="drop"
    )
    session.add_all([keep_note, drop_note])
    await session.commit()

    repo = SqliteArticleRepository(session)
    await repo.merge(keep_id=keep_id, drop_ids=[drop_id], user_id="u1")

    rows = (await session.execute(select(ArticleNote))).scalars().all()
    assert len(rows) == 1
    assert rows[0].content == "keep"


@pytest.mark.asyncio
async def test_merge_rewrites_screening_records_when_distinct_stages(
    session: AsyncSession,
):
    pid = await _seed_project(session)
    rid = await _seed_review(session, pid=pid)
    keep_id = await _seed_article(session, pid=pid)
    drop_id = await _seed_article(session, pid=pid, title="Drop")
    s_drop = ScreeningRecord(
        id=new_id(),
        user_id="u1",
        review_id=rid,
        article_id=drop_id,
        stage="title_abstract",
        decision="include",
    )
    s_keep = ScreeningRecord(
        id=new_id(),
        user_id="u1",
        review_id=rid,
        article_id=keep_id,
        stage="full_text",
        decision="include",
    )
    session.add_all([s_drop, s_keep])
    await session.commit()

    repo = SqliteArticleRepository(session)
    await repo.merge(keep_id=keep_id, drop_ids=[drop_id], user_id="u1")

    await session.refresh(s_drop)
    await session.refresh(s_keep)
    assert {s_drop.stage, s_keep.stage} == {"title_abstract", "full_text"}
    assert s_drop.article_id == keep_id
    assert s_keep.article_id == keep_id


@pytest.mark.asyncio
async def test_merge_deletes_screening_record_when_keep_already_has_same_stage(
    session: AsyncSession,
):
    pid = await _seed_project(session)
    rid = await _seed_review(session, pid=pid)
    keep_id = await _seed_article(session, pid=pid)
    drop_id = await _seed_article(session, pid=pid, title="Drop")
    s_keep = ScreeningRecord(
        id=new_id(),
        user_id="u1",
        review_id=rid,
        article_id=keep_id,
        stage="title_abstract",
        decision="include",
    )
    s_drop = ScreeningRecord(
        id=new_id(),
        user_id="u1",
        review_id=rid,
        article_id=drop_id,
        stage="title_abstract",
        decision="exclude",
    )
    session.add_all([s_keep, s_drop])
    await session.commit()

    repo = SqliteArticleRepository(session)
    await repo.merge(keep_id=keep_id, drop_ids=[drop_id], user_id="u1")

    rows = (await session.execute(select(ScreeningRecord))).scalars().all()
    assert len(rows) == 1
    assert rows[0].decision == "include"  # keep won


@pytest.mark.asyncio
async def test_merge_rewrites_rob_assessments_with_distinct_tools(
    session: AsyncSession,
):
    pid = await _seed_project(session)
    rid = await _seed_review(session, pid=pid)
    keep_id = await _seed_article(session, pid=pid)
    drop_id = await _seed_article(session, pid=pid, title="Drop")
    r1 = RobAssessment(
        id=new_id(),
        user_id="u1",
        review_id=rid,
        article_id=drop_id,
        tool="rob2",
        domain_answers={},
        overall_auto="low",
    )
    r2 = RobAssessment(
        id=new_id(),
        user_id="u1",
        review_id=rid,
        article_id=keep_id,
        tool="robins_i",
        domain_answers={},
        overall_auto="low",
    )
    session.add_all([r1, r2])
    await session.commit()

    repo = SqliteArticleRepository(session)
    await repo.merge(keep_id=keep_id, drop_ids=[drop_id], user_id="u1")

    await session.refresh(r1)
    await session.refresh(r2)
    assert {r1.tool, r2.tool} == {"rob2", "robins_i"}
    assert r1.article_id == keep_id
    assert r2.article_id == keep_id


@pytest.mark.asyncio
async def test_merge_rewrites_extraction_records_when_keep_has_none(
    session: AsyncSession,
):
    pid = await _seed_project(session)
    rid = await _seed_review(session, pid=pid)
    keep_id = await _seed_article(session, pid=pid)
    drop_id = await _seed_article(session, pid=pid, title="Drop")
    e = ExtractionRecord(
        id=new_id(),
        user_id="u1",
        review_id=rid,
        article_id=drop_id,
        fields={"n": 100},
    )
    session.add(e)
    await session.commit()

    repo = SqliteArticleRepository(session)
    await repo.merge(keep_id=keep_id, drop_ids=[drop_id], user_id="u1")

    await session.refresh(e)
    assert e.article_id == keep_id


@pytest.mark.asyncio
async def test_merge_deletes_drop_extraction_when_keep_already_has_one(
    session: AsyncSession,
):
    pid = await _seed_project(session)
    rid = await _seed_review(session, pid=pid)
    keep_id = await _seed_article(session, pid=pid)
    drop_id = await _seed_article(session, pid=pid, title="Drop")
    e_keep = ExtractionRecord(
        id=new_id(),
        user_id="u1",
        review_id=rid,
        article_id=keep_id,
        fields={"n": 50},
    )
    e_drop = ExtractionRecord(
        id=new_id(),
        user_id="u1",
        review_id=rid,
        article_id=drop_id,
        fields={"n": 100},
    )
    session.add_all([e_keep, e_drop])
    await session.commit()

    repo = SqliteArticleRepository(session)
    await repo.merge(keep_id=keep_id, drop_ids=[drop_id], user_id="u1")

    rows = (
        await session.execute(select(ExtractionRecord))
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].fields == {"n": 50}


@pytest.mark.asyncio
async def test_merge_rewrites_meta_inputs_when_present(session: AsyncSession):
    """Phase 7.5 cross-link — MetaInput.article_id rewired."""
    pid = await _seed_project(session)
    rid = await _seed_review(session, pid=pid)
    keep_id = await _seed_article(session, pid=pid)
    drop_id = await _seed_article(session, pid=pid, title="Drop")
    ma = MetaAnalysis(
        id=new_id(),
        user_id="u1",
        review_id=rid,
        effect_metric="or",
        model="random",
    )
    session.add(ma)
    await session.commit()
    mi = MetaInput(
        id=new_id(),
        user_id="u1",
        meta_id=ma.id,
        article_id=drop_id,
    )
    session.add(mi)
    await session.commit()

    repo = SqliteArticleRepository(session)
    await repo.merge(keep_id=keep_id, drop_ids=[drop_id], user_id="u1")

    await session.refresh(mi)
    assert mi.article_id == keep_id


@pytest.mark.asyncio
async def test_merge_refuses_same_id(session: AsyncSession):
    pid = await _seed_project(session)
    keep_id = await _seed_article(session, pid=pid)

    repo = SqliteArticleRepository(session)
    with pytest.raises(ValueError, match="merge an article into itself"):
        await repo.merge(
            keep_id=keep_id, drop_ids=[keep_id], user_id="u1"
        )


@pytest.mark.asyncio
async def test_merge_refuses_cross_project(session: AsyncSession):
    p1 = await _seed_project(session)
    p2 = await _seed_project(session)
    keep_id = await _seed_article(session, pid=p1)
    drop_id = await _seed_article(session, pid=p2)

    repo = SqliteArticleRepository(session)
    with pytest.raises(ValueError, match="cross-project"):
        await repo.merge(
            keep_id=keep_id, drop_ids=[drop_id], user_id="u1"
        )


@pytest.mark.asyncio
async def test_merge_refuses_cross_user(session: AsyncSession):
    pid = await _seed_project(session)
    keep_id = await _seed_article(session, pid=pid)
    # Another user's article in the same project schema, simulated via direct insert
    other = Article(
        id=new_id(),
        user_id="u2",
        project_id=pid,
        title="Other user's article",
        source="upload",
    )
    session.add(other)
    await session.commit()

    repo = SqliteArticleRepository(session)
    with pytest.raises(ValueError, match="not found"):
        await repo.merge(
            keep_id=keep_id, drop_ids=[other.id], user_id="u1"
        )


@pytest.mark.asyncio
async def test_merge_returns_keep_row(session: AsyncSession):
    pid = await _seed_project(session)
    keep_id = await _seed_article(session, pid=pid, title="Keeper")
    drop_id = await _seed_article(session, pid=pid, title="Drop")

    repo = SqliteArticleRepository(session)
    kept = await repo.merge(keep_id=keep_id, drop_ids=[drop_id], user_id="u1")
    assert kept.id == keep_id
    assert kept.title == "Keeper"


@pytest.mark.asyncio
async def test_merge_drops_get_deleted_after_rewiring(session: AsyncSession):
    pid = await _seed_project(session)
    keep_id = await _seed_article(session, pid=pid)
    drop_id = await _seed_article(session, pid=pid, title="Drop")

    repo = SqliteArticleRepository(session)
    await repo.merge(keep_id=keep_id, drop_ids=[drop_id], user_id="u1")

    remaining = (await session.execute(select(Article))).scalars().all()
    assert {r.id for r in remaining} == {keep_id}


@pytest.mark.asyncio
async def test_merge_handles_multiple_drops(session: AsyncSession):
    pid = await _seed_project(session)
    keep_id = await _seed_article(session, pid=pid)
    drop1 = await _seed_article(session, pid=pid, title="d1")
    drop2 = await _seed_article(session, pid=pid, title="d2")

    repo = SqliteArticleRepository(session)
    await repo.merge(
        keep_id=keep_id, drop_ids=[drop1, drop2], user_id="u1"
    )

    remaining = (await session.execute(select(Article))).scalars().all()
    assert {r.id for r in remaining} == {keep_id}
