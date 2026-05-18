"""Verify SQLite foreign-key PRAGMA is enabled app-wide via connect listener."""
from __future__ import annotations

import pytest
from sqlalchemy import text

from research_api.db.base import Base, make_engine, make_session_factory


@pytest.mark.asyncio
async def test_pragma_foreign_keys_on_for_new_engine(tmp_path):
    url = f"sqlite+aiosqlite:///{tmp_path}/pragma.db"
    engine = make_engine(url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = make_session_factory(engine)
    async with factory() as s:
        result = await s.execute(text("PRAGMA foreign_keys"))
        assert result.scalar_one() == 1
    await engine.dispose()


@pytest.mark.asyncio
async def test_cascade_delete_works_without_manual_pragma(tmp_path):
    """Parent delete must cascade to child rows automatically — no per-session PRAGMA."""
    from research_api.db.models import Dataset, DatasetVariable, Project

    url = f"sqlite+aiosqlite:///{tmp_path}/cascade.db"
    engine = make_engine(url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = make_session_factory(engine)
    async with factory() as s:
        p = Project(user_id="u", title="P", study_type="Outcome Study")
        s.add(p)
        await s.flush()
        ds = Dataset(
            user_id="u",
            project_id=p.id,
            filename="d.csv",
            file_ref={"backend": "local", "key": "k"},
            file_type="text/csv",
            n_rows=1,
            n_columns=1,
        )
        s.add(ds)
        await s.flush()
        s.add(
            DatasetVariable(
                user_id="u",
                dataset_id=ds.id,
                name="x",
                position=0,
                inferred_type="numeric",
                n_missing=0,
                sample_values=[],
            )
        )
        await s.commit()

        await s.execute(text("DELETE FROM datasets WHERE id = :id"), {"id": ds.id})
        await s.commit()

        rows = (await s.execute(text("SELECT id FROM dataset_variables"))).all()
        assert rows == []
    await engine.dispose()
