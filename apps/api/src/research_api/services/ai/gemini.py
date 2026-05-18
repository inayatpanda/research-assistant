"""Gemini AI provider with the §6.2 robustness layer.

Architecture: a GeminiClient port (Protocol) handles the SDK boundary so the provider
can be tested with a fake. The real client adapter is RealGeminiClient.
"""
from __future__ import annotations

import asyncio
import json
import random
from typing import Any, Protocol

from pydantic import ValidationError

from .base import AIProvider, CardContext, SectionDraftContext, WritingAction
from .errors import (
    AIError,
    AIProviderUnavailable,
    AIRateLimited,
    AISourceInsufficient,
)
from .model_chain import ModelChain
from .prompts import (
    CARD_DRAFT_PROMPT,
    EXTRACTION_PROMPT,
    SECTION_DRAFT_PROMPT,
    SUMMARISE_PROMPT,
    WRITING_ASSIST_PROMPT,
    build_meta_interpretation_prompt,
    build_result_interpretation_prompt,
    build_screening_suggestion_prompt,
    format_card_for_prompt,
)
from .schemas import CitationMetadata

GEMINI_MODEL_CHAIN: tuple[str, ...] = (
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash-latest",
    "gemini-1.5-flash-002",
)


class TransientError(Exception):
    """Marker for retryable errors (429, 503, network)."""


class ModelNotFoundError(Exception):
    """Marker for 'model name is dead' — triggers chain demotion."""


class GeminiClient(Protocol):
    """SDK boundary. Tests substitute a FakeGeminiClient."""

    async def list_models(self) -> list[str]: ...

    async def generate(self, model: str, prompt: str) -> str: ...


class GeminiProvider(AIProvider):
    name = "gemini"

    def __init__(
        self,
        client: GeminiClient,
        *,
        chain: tuple[str, ...] = GEMINI_MODEL_CHAIN,
        max_retries: int = 3,
        backoff_base: float = 1.0,
        jitter: float = 0.25,
    ) -> None:
        self._client = client
        self._initial_chain = chain
        self._chain: ModelChain | None = None
        self._max_retries = max_retries
        self._backoff_base = backoff_base
        self._jitter = jitter

    @property
    def active_model(self) -> str | None:
        return self._chain.active if self._chain else None

    async def _ensure_chain(self) -> ModelChain:
        if self._chain is None:
            available = set(await self._client.list_models())
            self._chain = ModelChain.resolve(available, self._initial_chain, provider="gemini")
        return self._chain

    async def _generate_with_resilience(self, prompt: str) -> str:
        chain = await self._ensure_chain()
        while True:
            try:
                return await self._call_with_retries(chain.active, prompt)
            except ModelNotFoundError:
                # Persistent 404 — demote this model and try the next chain member.
                chain = chain.demote()
                self._chain = chain
                continue

    async def _call_with_retries(self, model: str, prompt: str) -> str:
        last_err: Exception | None = None
        for attempt in range(1, self._max_retries + 1):
            try:
                return await self._client.generate(model, prompt)
            except ModelNotFoundError:
                raise
            except TransientError as e:
                last_err = e
                if attempt == self._max_retries:
                    raise AIRateLimited(
                        f"transient errors exhausted on {model}: {e}", provider="gemini"
                    ) from e
                backoff = self._backoff_base * (2 ** (attempt - 1))
                jitter = random.uniform(0, self._jitter)
                await asyncio.sleep(backoff + jitter)
        # Unreachable, but keeps type-checker calm
        raise AIRateLimited("retries exhausted", provider="gemini") from last_err

    async def extract_citation(self, pdf_text: str) -> CitationMetadata:
        if not pdf_text or len(pdf_text.strip()) < 50:
            raise AISourceInsufficient("text too short to extract", provider="gemini")
        prompt = EXTRACTION_PROMPT.format(text=pdf_text[:6000])
        raw = await self._generate_with_resilience(prompt)
        return _parse_citation_json(raw)

    async def summarise(self, text: str, max_sentences: int = 2) -> str:
        if not text or len(text.strip()) < 20:
            raise AISourceInsufficient("text too short to summarise", provider="gemini")
        prompt = SUMMARISE_PROMPT.format(text=text, max_sentences=max_sentences)
        raw = (await self._generate_with_resilience(prompt)).strip()
        if raw == "INSUFFICIENT_SOURCE":
            raise AISourceInsufficient("model rejected the passage", provider="gemini")
        return raw

    async def generate_card_draft(self, ctx: CardContext) -> str:
        if not ctx.selected_text or len(ctx.selected_text.strip()) < 5:
            raise AISourceInsufficient("source passage too short to draft", provider="gemini")
        prompt = CARD_DRAFT_PROMPT.format(
            section=ctx.section,
            cite_tag=f"[CITE_{ctx.cite_tag}]",
            selected_text=ctx.selected_text,
            user_note=(ctx.user_note or "").strip() or "(no paraphrase)",
        )
        raw = (await self._generate_with_resilience(prompt)).strip()
        return raw

    async def generate_section_draft(self, ctx: SectionDraftContext) -> str:
        if not ctx.cards:
            raise AISourceInsufficient("no cards to draft from", provider="gemini")
        cards_block = "\n\n".join(
            format_card_for_prompt(
                tag=f"[CITE_{c.cite_tag}]",
                selected_text=c.selected_text,
                user_note=c.user_note,
            )
            for c in ctx.cards
        )
        prompt = SECTION_DRAFT_PROMPT.format(section=ctx.section, cards_block=cards_block)
        raw = (await self._generate_with_resilience(prompt)).strip()
        return raw

    async def interpret_result(
        self,
        *,
        test_label: str,
        rationale: str,
        summary: dict[str, Any],
        assumptions: dict[str, Any] | None,
        cite_token: str,
    ) -> str:
        if not cite_token or not cite_token.strip():
            raise AISourceInsufficient("missing cite_token", provider="gemini")
        prompt = build_result_interpretation_prompt(
            test_label=test_label,
            rationale=rationale,
            summary=summary,
            assumptions=assumptions,
            cite_token=cite_token,
        )
        return (await self._generate_with_resilience(prompt)).strip()

    async def assist_writing(self, text: str, action: WritingAction) -> str:
        if not text or len(text.strip()) < 5:
            raise AISourceInsufficient("text too short to assist", provider="gemini")
        prompt = WRITING_ASSIST_PROMPT.format(action=action, text=text)
        return (await self._generate_with_resilience(prompt)).strip()

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
        if not studies:
            raise AISourceInsufficient("no studies to interpret", provider="gemini")
        if pooled.get("estimate") is None:
            raise AISourceInsufficient("missing pooled estimate", provider="gemini")
        prompt = build_meta_interpretation_prompt(
            metric=metric,
            model=model,
            pooled=pooled,
            heterogeneity=heterogeneity,
            studies=studies,
            subgroups=subgroups,
        )
        return (await self._generate_with_resilience(prompt)).strip()

    async def suggest_screening(
        self,
        *,
        eligibility_inclusion: str | None,
        eligibility_exclusion: str | None,
        pico: dict[str, str | None],
        article_title: str,
        article_abstract: str | None,
    ) -> dict[str, str]:
        if not (article_title or "").strip():
            raise AISourceInsufficient("missing article title", provider="gemini")
        system, user = build_screening_suggestion_prompt(
            eligibility_inclusion=eligibility_inclusion,
            eligibility_exclusion=eligibility_exclusion,
            pico=pico,
            article_title=article_title,
            article_abstract=article_abstract,
        )
        raw = (await self._generate_with_resilience(f"{system}\n\n{user}")).strip()
        vote, reason = _parse_screening_json(raw)
        return {"vote": vote, "reason": reason, "model": self.active_model or "unknown"}


_ALLOWED_SCREENING_VOTES = frozenset({"include", "exclude", "maybe"})


def _parse_screening_json(raw: str) -> tuple[str, str]:
    stripped = raw.strip()
    if stripped.startswith("```"):
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start != -1 and end != -1 and end > start:
            stripped = stripped[start : end + 1]
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError as e:
        raise AIError(
            f"could not parse JSON from model: {e}; raw[:200]={raw[:200]!r}",
            provider="gemini",
        ) from e
    if not isinstance(data, dict):
        raise AIError("screening output is not a JSON object", provider="gemini")
    vote = data.get("vote")
    reason = data.get("reason")
    if not isinstance(vote, str) or not isinstance(reason, str):
        raise AIError(
            f"screening output missing required keys; got {list(data.keys())!r}",
            provider="gemini",
        )
    vote_norm = vote.strip().lower()
    if vote_norm not in _ALLOWED_SCREENING_VOTES:
        raise AIError(
            f"screening vote {vote!r} not in {sorted(_ALLOWED_SCREENING_VOTES)}",
            provider="gemini",
        )
    return vote_norm, reason.strip()


def _parse_citation_json(raw: str) -> CitationMetadata:
    # Tolerate ```json ... ``` fences or stray prose
    stripped = raw.strip()
    if stripped.startswith("```"):
        # Find first { and last }
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start != -1 and end != -1 and end > start:
            stripped = stripped[start : end + 1]
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError as e:
        raise AIProviderUnavailable(
            f"could not parse JSON from model: {e}; raw[:200]={raw[:200]!r}", provider="gemini"
        ) from e
    try:
        return CitationMetadata(**data)
    except ValidationError as e:
        raise AIProviderUnavailable(
            f"model JSON did not match CitationMetadata schema: {e}", provider="gemini"
        ) from e
