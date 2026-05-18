"""Shared test fixtures."""
from pathlib import Path

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from research_api.db.base import Base, make_engine, make_session_factory
from research_api.services.ai import AIProvider, CardContext, CitationMetadata, SectionDraftContext
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

    async def generate_card_draft(self, ctx: CardContext) -> str:
        return f"This study reported on the topic [CITE_{ctx.cite_tag}]."

    async def generate_section_draft(self, ctx: SectionDraftContext) -> str:
        return " ".join(f"Finding [CITE_{c.cite_tag}]." for c in ctx.cards)

    async def interpret_result(
        self,
        *,
        test_label: str,
        rationale: str,
        summary: dict,
        assumptions: dict | None,
        cite_token: str,
    ) -> str:
        self.calls.append("interpret_result")
        return (
            f"Test {test_label}: statistic={summary.get('statistic')}, "
            f"p={summary.get('p_value')}. {cite_token}"
        )

    async def assist_writing(self, text: str, action: WritingAction) -> str:
        # Preserve CITE tokens verbatim (mirrors the prompt's preservation rule)
        return f"[{action}] {text}"

    async def suggest_screening(
        self,
        *,
        eligibility_inclusion: str | None,
        eligibility_exclusion: str | None,
        pico: dict[str, str | None],
        article_title: str,
        article_abstract: str | None,
    ) -> dict[str, str]:
        self.calls.append("suggest_screening")
        return {
            "vote": "maybe",
            "reason": "fake-ai screening reason",
            "model": "fake-model",
        }

    async def interpret_meta_analysis(
        self,
        *,
        metric: str,
        model: str,
        pooled: dict,
        heterogeneity: dict,
        studies: list,
        subgroups: dict | None,
    ) -> str:
        self.calls.append("interpret_meta_analysis")
        tokens = " ".join(f"[CITE_{s['article_id']}]" for s in studies)
        est = pooled.get("estimate")
        return (
            f"Pooled {metric.upper()} = {est:.2f} from {len(studies)} studies "
            f"({model}-effects). {tokens}"
        )


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
