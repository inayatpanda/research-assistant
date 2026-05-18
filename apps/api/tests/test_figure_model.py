"""Phase 8.7 — Figure + ConsortData ORM model tests."""
from __future__ import annotations

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from research_api.db.models import ConsortData, Figure, Project, new_id


async def _seed_project(session, user_id: str = "u1") -> Project:
    p = Project(id=new_id(), user_id=user_id, title="P1", study_type="Randomised Controlled Trial")
    session.add(p)
    await session.commit()
    await session.refresh(p)
    return p


@pytest.mark.asyncio
async def test_figure_persists(session) -> None:
    proj = await _seed_project(session)
    fig = Figure(
        id=new_id(),
        user_id=proj.user_id,
        project_id=proj.id,
        file_ref={"backend": "local", "key": "u1/figures/abc/k.png"},
        file_type="image/png",
        figure_number=1,
        caption="My fig",
        alt_text="alt",
        width_px=100,
        height_px=80,
        byte_size=2048,
    )
    session.add(fig)
    await session.commit()
    rows = (await session.execute(select(Figure))).scalars().all()
    assert len(rows) == 1
    assert rows[0].figure_number == 1


@pytest.mark.asyncio
async def test_figure_uniqueness_per_project_user_number_violation_fires(session) -> None:
    proj = await _seed_project(session)
    f1 = Figure(
        id=new_id(), user_id=proj.user_id, project_id=proj.id,
        file_ref={"backend": "local", "key": "k1"}, file_type="image/png",
        figure_number=1, byte_size=10,
    )
    f2 = Figure(
        id=new_id(), user_id=proj.user_id, project_id=proj.id,
        file_ref={"backend": "local", "key": "k2"}, file_type="image/png",
        figure_number=1, byte_size=10,  # duplicate number for same project+user
    )
    session.add(f1)
    await session.commit()
    session.add(f2)
    with pytest.raises(IntegrityError):
        await session.commit()


@pytest.mark.asyncio
async def test_figure_cascades_when_project_deleted(session) -> None:
    # FK ON DELETE CASCADE — need to enable pragma in SQLite
    await session.execute(text("PRAGMA foreign_keys = ON"))
    proj = await _seed_project(session)
    fig = Figure(
        id=new_id(), user_id=proj.user_id, project_id=proj.id,
        file_ref={"backend": "local", "key": "k1"}, file_type="image/png",
        figure_number=1, byte_size=10,
    )
    session.add(fig)
    await session.commit()
    await session.execute(text(f"DELETE FROM projects WHERE id='{proj.id}'"))
    await session.commit()
    rows = (await session.execute(select(Figure))).scalars().all()
    assert rows == []


@pytest.mark.asyncio
async def test_consort_unique_per_project_user(session) -> None:
    proj = await _seed_project(session)
    c1 = ConsortData(id=new_id(), user_id=proj.user_id, project_id=proj.id, randomised=100)
    session.add(c1)
    await session.commit()
    c2 = ConsortData(id=new_id(), user_id=proj.user_id, project_id=proj.id, randomised=200)
    session.add(c2)
    with pytest.raises(IntegrityError):
        await session.commit()


@pytest.mark.asyncio
async def test_consort_allows_per_user_isolation(session) -> None:
    proj = await _seed_project(session, user_id="alice")
    session.add(ConsortData(id=new_id(), user_id="alice", project_id=proj.id, randomised=10))
    session.add(ConsortData(id=new_id(), user_id="bob",   project_id=proj.id, randomised=20))
    await session.commit()
    rows = (await session.execute(select(ConsortData))).scalars().all()
    assert {r.user_id for r in rows} == {"alice", "bob"}


@pytest.mark.asyncio
async def test_project_template_journal_nullable_and_persists(session) -> None:
    proj = await _seed_project(session)
    assert proj.template_journal is None
    proj.template_journal = "jbjs"
    await session.commit()
    await session.refresh(proj)
    assert proj.template_journal == "jbjs"
