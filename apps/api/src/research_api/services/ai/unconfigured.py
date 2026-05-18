"""Stub AIProvider used when no key is configured.

Every call raises AIProviderUnavailable so the rest of the stack treats it
exactly like an outage. The /health endpoint reports `ok=False, reason="no key"`.
"""
from __future__ import annotations

from typing import Any

from .base import AIProvider, CardContext, SectionDraftContext, WritingAction
from .errors import AIProviderUnavailable
from .schemas import CitationMetadata


class UnconfiguredAIProvider(AIProvider):
    def __init__(self, name: str = "gemini") -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def active_model(self) -> str | None:
        return None

    async def extract_citation(self, pdf_text: str) -> CitationMetadata:
        raise AIProviderUnavailable("no API key configured", provider=self._name)

    async def summarise(self, text: str, max_sentences: int = 2) -> str:
        raise AIProviderUnavailable("no API key configured", provider=self._name)

    async def generate_card_draft(self, ctx: CardContext) -> str:
        raise AIProviderUnavailable("no API key configured", provider=self._name)

    async def generate_section_draft(self, ctx: SectionDraftContext) -> str:
        raise AIProviderUnavailable("no API key configured", provider=self._name)

    async def interpret_result(
        self,
        *,
        test_label: str,
        rationale: str,
        summary: dict[str, Any],
        assumptions: dict[str, Any] | None,
        cite_token: str,
    ) -> str:
        raise AIProviderUnavailable("no API key configured", provider=self._name)

    async def assist_writing(self, text: str, action: WritingAction) -> str:
        raise AIProviderUnavailable("no API key configured", provider=self._name)

    async def suggest_screening(
        self,
        *,
        eligibility_inclusion: str | None,
        eligibility_exclusion: str | None,
        pico: dict[str, str | None],
        article_title: str,
        article_abstract: str | None,
    ) -> dict[str, str]:
        raise AIProviderUnavailable("no API key configured", provider=self._name)

    async def interpret_meta_analysis(
        self,
        *,
        metric: str,
        model: str,
        pooled: dict[str, float | None],
        heterogeneity: dict[str, float | int | None],
        studies: list[dict[str, str]],
        subgroups: dict[str, dict[str, float]] | None,
    ) -> str:
        raise AIProviderUnavailable("no API key configured", provider=self._name)

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
    ) -> dict[str, Any]:
        raise AIProviderUnavailable("no API key configured", provider=self._name)

    async def draft_reviewer_response(
        self,
        *,
        raw_comments: str,
        abstract: str | None,
    ) -> dict[str, Any]:
        raise AIProviderUnavailable("no API key configured", provider=self._name)
