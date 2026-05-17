"""Shared test fixtures."""
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from research_api.db.base import Base, make_engine, make_session_factory


@pytest_asyncio.fixture
async def session(tmp_path: Path) -> AsyncSession:
    """Per-test fresh SQLite DB + open AsyncSession."""
    url = f"sqlite+aiosqlite:///{tmp_path}/test.db"
    engine = make_engine(url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = make_session_factory(engine)
    async with factory() as s:
        yield s
    await engine.dispose()


@pytest_asyncio.fixture
async def client(tmp_path: Path, monkeypatch):
    """Per-test fresh DB + FastAPI app with overridden container."""
    monkeypatch.setenv("SQLITE_URL", f"sqlite+aiosqlite:///{tmp_path}/test.db")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    from research_api.container import build_container, set_container
    from research_api.main import app

    container = build_container()
    async with container.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    set_container(container)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

    await container.engine.dispose()
    set_container(None)  # reset for next test
