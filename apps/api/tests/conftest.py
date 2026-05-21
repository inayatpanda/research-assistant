"""Shared test fixtures."""
import os
from pathlib import Path

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

# Globally disable the APScheduler thread during tests — the lifespan honours
# this flag and never starts a real BackgroundScheduler. Tests that want to
# exercise the scheduler set up their own MemoryJobStore-backed instance.
os.environ.setdefault("SCHEDULER_DISABLED", "1")

# DEMO-FIX-D HIGH-1 — tests build their schema via ``Base.metadata.create_all``
# against a per-test temp SQLite file. Skip the lifespan's auto-migrate so we
# don't double-create tables (or run alembic against a non-canonical DB path).
# The startup-migration is exercised explicitly by tests that unset this flag.
os.environ.setdefault("DISABLE_AUTO_MIGRATE", "1")

# Phase S1 — keep the legacy static-user-id mode on by default for the
# existing 2260-test suite. Auth-specific tests (``test_auth_routes.py``,
# ``test_security_rbac.py`` etc.) flip this off explicitly with monkeypatch.
os.environ.setdefault("RMA_DISABLE_AUTH", "1")

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
        variables: dict | None = None,
        display_labels: dict[str, str] | None = None,
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

    async def draft_cover_letter(
        self,
        *,
        title: str,
        abstract: str | None,
        journal_label: str,
        novelty_points: list[str] | None,
        corresponding_name: str | None,
        corresponding_affiliation: str | None,
        corresponding_email: str | None,
        conflicts_statement: str | None,
    ) -> dict:
        self.calls.append("draft_cover_letter")
        bullets = "; ".join(novelty_points or []) or "(no novelty bullets)"
        coi = (conflicts_statement or "").strip() or "no conflicts"
        body = (
            f"<p>Dear Editor of {journal_label},</p>"
            f"<p>We submit \"{title}\" for consideration.</p>"
            f"<p>Novelty: {bullets}.</p>"
            f"<p>Conflicts: {coi}.</p>"
            f"<p>Sincerely, {corresponding_name or '(corresponding author)'}.</p>"
        )
        return {"body_html": body, "model": "fake-model"}

    async def draft_reviewer_response(
        self,
        *,
        raw_comments: str,
        abstract: str | None,
    ) -> dict:
        self.calls.append("draft_reviewer_response")
        # Deterministic fake segmenter: split on blank lines.
        chunks = [c.strip() for c in raw_comments.split("\n\n") if c.strip()]
        if not chunks:
            chunks = [raw_comments.strip() or "(empty)"]
        comments = [
            {
                "comment_text": chunk,
                "response_html": f"<p>We thank the reviewer for the comment. We have addressed point {i + 1}.</p>",
            }
            for i, chunk in enumerate(chunks)
        ]
        return {"comments": comments, "model": "fake-model"}

    async def peer_review(
        self,
        *,
        manuscript_text: str,
        title: str,
        study_type: str | None,
        metadata: dict[str, int] | None = None,
    ) -> dict:
        """Phase 4.6 — Deterministic fake peer-review critique.

        Reports the recommendation as ``major_revision`` unless the
        manuscript contains the substring ``ACCEPT_ME`` (test-only escape
        hatch). Every list key is populated with at least one entry so
        downstream rendering paths can be exercised.
        """
        self.calls.append("peer_review")
        rec = "accept" if "ACCEPT_ME" in (manuscript_text or "") else "major_revision"
        meta = metadata or {}
        return {
            "overall_impression": (
                f"Fake peer review of '{title}' (study_type={study_type or 'n/a'}, "
                f"text_len={len(manuscript_text or '')}, "
                f"figures={meta.get('n_figures', 0)}, "
                f"tables={meta.get('n_tables', 0)})."
            ),
            "strengths": [
                "Clear research question",
                "Reasonable sample size",
            ],
            "major_issues": [
                "Methods: randomisation procedure not described",
            ],
            "minor_issues": [
                "Abstract: word count exceeds 250",
            ],
            "methodological_concerns": [
                "Methods: blinding strategy not specified",
            ],
            "statistical_concerns": [
                "Results: no confidence intervals reported",
            ],
            "reporting_concerns": [
                "No CONSORT flow diagram",
            ],
            "presentation_concerns": [
                "Figure legends are terse",
            ],
            "references_concerns": [
                "Several DOIs missing from the reference list",
            ],
            "suggestions_for_improvement": [
                "Add CONSORT-compliant flow diagram",
                "Report effect sizes with 95% CIs",
            ],
            "recommendation": rec,
            "model": self._active_model,
        }

    async def interpret_economic_result(
        self,
        *,
        name: str,
        perspective: str,
        time_horizon_months: int,
        currency: str,
        discount_rate_costs: float,
        discount_rate_qalys: float,
        intervention_label: str,
        comparator_label: str,
        value_set: str,
        mean_cost_diff: float,
        mean_qaly_diff: float,
        icer: float | None,
        dominance_status: str,
        nmb_at_thresholds: dict | None,
        ceac_data: list | None,
        wtp_thresholds: list | None,
        sensitivity: dict | None,
        cite_token: str,
    ) -> str:
        self.calls.append("interpret_economic_result")
        return (
            f"Economic CEA {name}: dCost={mean_cost_diff:.2f}, "
            f"dQALY={mean_qaly_diff:.4f}, ICER={icer}, "
            f"dominance={dominance_status}. {cite_token}"
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
