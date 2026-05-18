"""Phase 8.7 — SqliteFigureRepository unit tests."""
from __future__ import annotations

import pytest

from research_api.db.models import Project, new_id
from research_api.repositories.figures import SqliteFigureRepository


async def _seed_project(session, user_id: str = "alice", title: str = "P") -> Project:
    p = Project(id=new_id(), user_id=user_id, title=title, study_type="Randomised Controlled Trial")
    session.add(p)
    await session.commit()
    await session.refresh(p)
    return p


def _ref(key: str = "k") -> dict:
    return {"backend": "local", "key": key}


@pytest.mark.asyncio
async def test_create_assigns_first_figure_number_1(session) -> None:
    proj = await _seed_project(session)
    repo = SqliteFigureRepository(session)
    fig = await repo.create(
        project_id=proj.id, user_id="alice", file_ref=_ref(),
        file_type="image/png", width_px=10, height_px=10, byte_size=100,
    )
    assert fig.figure_number == 1


@pytest.mark.asyncio
async def test_create_assigns_next_figure_number_after_existing(session) -> None:
    proj = await _seed_project(session)
    repo = SqliteFigureRepository(session)
    a = await repo.create(
        project_id=proj.id, user_id="alice", file_ref=_ref("a"),
        file_type="image/png", width_px=10, height_px=10, byte_size=100,
    )
    b = await repo.create(
        project_id=proj.id, user_id="alice", file_ref=_ref("b"),
        file_type="image/png", width_px=10, height_px=10, byte_size=100,
    )
    c = await repo.create(
        project_id=proj.id, user_id="alice", file_ref=_ref("c"),
        file_type="image/png", width_px=10, height_px=10, byte_size=100,
    )
    assert [a.figure_number, b.figure_number, c.figure_number] == [1, 2, 3]


@pytest.mark.asyncio
async def test_create_isolates_numbering_per_project(session) -> None:
    p1 = await _seed_project(session, title="P1")
    p2 = await _seed_project(session, title="P2")
    repo = SqliteFigureRepository(session)
    await repo.create(
        project_id=p1.id, user_id="alice", file_ref=_ref(), file_type="image/png",
        width_px=10, height_px=10, byte_size=100,
    )
    f2 = await repo.create(
        project_id=p2.id, user_id="alice", file_ref=_ref(), file_type="image/png",
        width_px=10, height_px=10, byte_size=100,
    )
    assert f2.figure_number == 1


@pytest.mark.asyncio
async def test_list_returns_sorted_by_figure_number(session) -> None:
    proj = await _seed_project(session)
    repo = SqliteFigureRepository(session)
    for _ in range(3):
        await repo.create(
            project_id=proj.id, user_id="alice", file_ref=_ref(), file_type="image/png",
            width_px=10, height_px=10, byte_size=100,
        )
    rows = await repo.list(project_id=proj.id, user_id="alice")
    assert [r.figure_number for r in rows] == [1, 2, 3]


@pytest.mark.asyncio
async def test_update_caption_and_alt_text(session) -> None:
    proj = await _seed_project(session)
    repo = SqliteFigureRepository(session)
    f = await repo.create(
        project_id=proj.id, user_id="alice", file_ref=_ref(), file_type="image/png",
        width_px=10, height_px=10, byte_size=100,
    )
    updated = await repo.update(f.id, "alice", caption="new", alt_text="alt")
    assert updated is not None
    assert updated.caption == "new"
    assert updated.alt_text == "alt"


@pytest.mark.asyncio
async def test_reorder_rewrites_figure_numbers_coherently(session) -> None:
    proj = await _seed_project(session)
    repo = SqliteFigureRepository(session)
    a = await repo.create(
        project_id=proj.id, user_id="alice", file_ref=_ref("a"), file_type="image/png",
        width_px=10, height_px=10, byte_size=100,
    )
    b = await repo.create(
        project_id=proj.id, user_id="alice", file_ref=_ref("b"), file_type="image/png",
        width_px=10, height_px=10, byte_size=100,
    )
    c = await repo.create(
        project_id=proj.id, user_id="alice", file_ref=_ref("c"), file_type="image/png",
        width_px=10, height_px=10, byte_size=100,
    )
    reordered = await repo.reorder(
        project_id=proj.id, user_id="alice", ordered_ids=[c.id, a.id, b.id]
    )
    by_id = {r.id: r.figure_number for r in reordered}
    assert by_id[c.id] == 1
    assert by_id[a.id] == 2
    assert by_id[b.id] == 3


@pytest.mark.asyncio
async def test_reorder_rejects_when_ids_do_not_match_project_set(session) -> None:
    proj = await _seed_project(session)
    repo = SqliteFigureRepository(session)
    f = await repo.create(
        project_id=proj.id, user_id="alice", file_ref=_ref(), file_type="image/png",
        width_px=10, height_px=10, byte_size=100,
    )
    with pytest.raises(ValueError):
        await repo.reorder(
            project_id=proj.id, user_id="alice", ordered_ids=[f.id, "nonexistent"]
        )


@pytest.mark.asyncio
async def test_delete_recompacts_remaining_numbers(session) -> None:
    proj = await _seed_project(session)
    repo = SqliteFigureRepository(session)
    a = await repo.create(
        project_id=proj.id, user_id="alice", file_ref=_ref("a"), file_type="image/png",
        width_px=10, height_px=10, byte_size=100,
    )
    b = await repo.create(
        project_id=proj.id, user_id="alice", file_ref=_ref("b"), file_type="image/png",
        width_px=10, height_px=10, byte_size=100,
    )
    c = await repo.create(
        project_id=proj.id, user_id="alice", file_ref=_ref("c"), file_type="image/png",
        width_px=10, height_px=10, byte_size=100,
    )
    deleted = await repo.delete(b.id, "alice")
    assert deleted is not None
    remaining = await repo.list(project_id=proj.id, user_id="alice")
    assert [r.id for r in remaining] == [a.id, c.id]
    assert [r.figure_number for r in remaining] == [1, 2]


@pytest.mark.asyncio
async def test_delete_returns_deleted_row_for_storage_cleanup(session) -> None:
    proj = await _seed_project(session)
    repo = SqliteFigureRepository(session)
    f = await repo.create(
        project_id=proj.id, user_id="alice",
        file_ref={"backend": "local", "key": "alice/figures/x/foo.png"},
        file_type="image/png", width_px=10, height_px=10, byte_size=100,
    )
    deleted = await repo.delete(f.id, "alice")
    assert deleted is not None
    assert deleted.file_ref["key"] == "alice/figures/x/foo.png"


@pytest.mark.asyncio
async def test_get_404_for_other_user(session) -> None:
    proj = await _seed_project(session, user_id="alice")
    repo = SqliteFigureRepository(session)
    f = await repo.create(
        project_id=proj.id, user_id="alice", file_ref=_ref(), file_type="image/png",
        width_px=10, height_px=10, byte_size=100,
    )
    other = await repo.get(f.id, "bob")
    assert other is None


@pytest.mark.asyncio
async def test_delete_returns_none_for_other_user(session) -> None:
    proj = await _seed_project(session, user_id="alice")
    repo = SqliteFigureRepository(session)
    f = await repo.create(
        project_id=proj.id, user_id="alice", file_ref=_ref(), file_type="image/png",
        width_px=10, height_px=10, byte_size=100,
    )
    result = await repo.delete(f.id, "bob")
    assert result is None
