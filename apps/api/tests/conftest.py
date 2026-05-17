"""Shared test fixtures."""
from pathlib import Path

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from research_api.db.base import Base, make_engine, make_session_factory
from research_api.services.ai import AIProvider, CitationMetadata
from research_api.services.ai.base import WritingAction


class FakeAIProvider(AIProvider):
    """Test double — returns deterministic metadata without any network call."""

    name = "gemini"

    def __init__(self) -> None:
        self._active_model = "gemini-2.5-flash"
        self.calls: list[str] = []

    @property
    def active_model(self) -> str | None:
        return self._active_model

    async def extract_citation(self, pdf_text: str) -> CitationMetadata:
        self.calls.append("extract_citation")
        return CitationMetadata(
            title="Fake Title from AI",
            authors=["First Author", "Second Author"],
            journal="Fake Journal",
            year=2024,
            doi="10.1234/fake.2024",
            confidence=0.9,
        )

    async def summarise(self, text: str, max_sentences: int = 2) -> str:
        return f"Summary of: {text[:30]}"

    async def generate_draft(self, ctx: dict) -> str:
        return "AI draft"

    async def interpret_result(self, test: str, output: dict) -> str:
        return "AI interpretation"

    async def assist_writing(self, text: str, action: WritingAction) -> str:
        return f"AI {action}: {text}"


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
    """Per-test fresh DB + FastAPI app with a Container holding fakes (FakeAI + tmp storage)."""
    monkeypatch.setenv("SQLITE_URL", f"sqlite+aiosqlite:///{tmp_path}/test.db")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("API_SIGNING_SECRET", "test-secret")

    from research_api.container import build_container, set_container
    from research_api.main import app
    from research_api.services.storage import LocalFsStorage

    settings_overrides = {}
    fake_ai = FakeAIProvider()
    container = build_container(
        ai=fake_ai,
        storage=LocalFsStorage(root=tmp_path, signing_secret="test-secret"),
    )
    async with container.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    set_container(container)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        # Expose the fake AI for assertion in tests via `c.fake_ai`
        c.fake_ai = fake_ai  # type: ignore[attr-defined]
        yield c

    await container.engine.dispose()
    set_container(None)
