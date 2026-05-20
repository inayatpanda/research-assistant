from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Protocol

from .schemas import CitationMetadata

WritingAction = Literal["improve", "shorten", "formalise", "add_transition"]


@dataclass(frozen=True)
class CardContext:
    """Inputs the AI provider needs to draft a single-sentence card."""

    cite_tag: str           # bare tag, e.g. "a1" — the provider wraps it as [CITE_a1]
    section: str            # 'Introduction' / 'Methodology' / 'Results' / 'Discussion'
    selected_text: str      # the highlighted passage
    user_note: str | None   # the user's paraphrase, may be empty


@dataclass(frozen=True)
class SectionDraftContext:
    """Inputs the AI provider needs to draft a multi-card paragraph."""

    section: str
    cards: list[CardContext]


class AIProvider(Protocol):
    """Vendor-neutral interface. Concrete implementations: GeminiProvider, ClaudeProvider, OpenAIProvider."""

    @property
    def name(self) -> str: ...

    @property
    def active_model(self) -> str | None: ...

    async def extract_citation(self, pdf_text: str) -> CitationMetadata: ...

    async def summarise(self, text: str, max_sentences: int = 2) -> str: ...

    async def generate_card_draft(self, ctx: CardContext) -> str: ...

    async def generate_section_draft(self, ctx: SectionDraftContext) -> str: ...

    # Phase 5/6 stubs
    async def assist_writing(self, text: str, action: WritingAction) -> str: ...
    async def interpret_result(
        self,
        *,
        test_label: str,
        rationale: str,
        summary: dict[str, Any],
        assumptions: dict[str, Any] | None,
        cite_token: str,
        variables: dict[str, Any] | None = None,
        display_labels: dict[str, str] | None = None,
    ) -> str: ...

    # Phase 7
    async def suggest_screening(
        self,
        *,
        eligibility_inclusion: str | None,
        eligibility_exclusion: str | None,
        pico: dict[str, str | None],
        article_title: str,
        article_abstract: str | None,
    ) -> dict[str, str]: ...

    # Phase 7.5
    async def interpret_meta_analysis(
        self,
        *,
        metric: str,
        model: str,
        pooled: dict[str, float | None],
        heterogeneity: dict[str, float | int | None],
        studies: list[dict[str, str]],
        subgroups: dict[str, dict[str, float]] | None,
    ) -> str: ...

    # Phase 12
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
    ) -> dict[str, Any]: ...

    async def draft_reviewer_response(
        self,
        *,
        raw_comments: str,
        abstract: str | None,
    ) -> dict[str, Any]: ...
