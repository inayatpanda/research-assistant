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
    build_cover_letter_prompt,
    build_meta_interpretation_prompt,
    build_peer_review_prompt,
    build_result_interpretation_prompt,
    build_reviewer_response_prompt,
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
        variables: dict[str, Any] | None = None,
        display_labels: dict[str, str] | None = None,
    ) -> str:
        if not cite_token or not cite_token.strip():
            raise AISourceInsufficient("missing cite_token", provider="gemini")
        prompt = build_result_interpretation_prompt(
            test_label=test_label,
            rationale=rationale,
            summary=summary,
            assumptions=assumptions,
            cite_token=cite_token,
            variables=variables,
            display_labels=display_labels,
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
        if not (title or "").strip():
            raise AISourceInsufficient("missing manuscript title", provider="gemini")
        system, user = build_cover_letter_prompt(
            title=title,
            abstract=abstract,
            journal_label=journal_label,
            novelty_points=novelty_points,
            corresponding_name=corresponding_name,
            corresponding_affiliation=corresponding_affiliation,
            corresponding_email=corresponding_email,
            conflicts_statement=conflicts_statement,
        )
        raw = (await self._generate_with_resilience(f"{system}\n\n{user}")).strip()
        body_html = _strip_md_fences(raw)
        return {"body_html": body_html, "model": self.active_model or "unknown"}

    async def draft_reviewer_response(
        self,
        *,
        raw_comments: str,
        abstract: str | None,
    ) -> dict[str, Any]:
        if not (raw_comments or "").strip():
            raise AISourceInsufficient(
                "missing reviewer comments", provider="gemini"
            )
        system, user = build_reviewer_response_prompt(
            raw_comments=raw_comments, abstract=abstract
        )
        raw = (await self._generate_with_resilience(f"{system}\n\n{user}")).strip()
        comments = _parse_reviewer_response_json(raw)
        return {"comments": comments, "model": self.active_model or "unknown"}

    async def peer_review(
        self,
        *,
        manuscript_text: str,
        title: str,
        study_type: str | None,
        metadata: dict[str, int] | None = None,
    ) -> dict[str, Any]:
        if not (manuscript_text or "").strip() or len(manuscript_text.strip()) < 200:
            raise AISourceInsufficient(
                "manuscript too short to peer-review", provider="gemini"
            )
        system, user = build_peer_review_prompt(
            title=title,
            study_type=study_type,
            manuscript_text=manuscript_text,
            metadata=metadata,
        )
        raw = await self._generate_with_resilience(f"{system}\n\n{user}")
        critique = _parse_peer_review_json(raw)
        critique["model"] = self.active_model or "unknown"
        return critique

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
        nmb_at_thresholds: dict[str, Any] | None,
        ceac_data: list[dict[str, Any]] | None,
        wtp_thresholds: list[int] | None,
        sensitivity: dict[str, Any] | None,
        cite_token: str,
    ) -> str:
        if not cite_token or not cite_token.strip():
            raise AISourceInsufficient("missing cite_token", provider="gemini")
        from .prompts import build_economic_interpretation_prompt

        prompt = build_economic_interpretation_prompt(
            name=name,
            perspective=perspective,
            time_horizon_months=time_horizon_months,
            currency=currency,
            discount_rate_costs=discount_rate_costs,
            discount_rate_qalys=discount_rate_qalys,
            intervention_label=intervention_label,
            comparator_label=comparator_label,
            value_set=value_set,
            mean_cost_diff=mean_cost_diff,
            mean_qaly_diff=mean_qaly_diff,
            icer=icer,
            dominance_status=dominance_status,
            nmb_at_thresholds=nmb_at_thresholds,
            ceac_data=ceac_data,
            wtp_thresholds=wtp_thresholds,
            sensitivity=sensitivity,
            cite_token=cite_token,
        )
        return (await self._generate_with_resilience(prompt)).strip()


def _strip_md_fences(raw: str) -> str:
    """Strip ```...``` fences if the model wrapped its output."""
    text = raw.strip()
    if text.startswith("```"):
        # Drop the opening fence line.
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def _parse_reviewer_response_json(raw: str) -> list[dict[str, str]]:
    """Parse the reviewer-response JSON envelope.

    Tolerates ```json fences (mirrors `_parse_screening_json`). Raises
    AIError when the shape is wrong (not an object, missing `comments`,
    rows missing `comment_text` / `response_html`, etc.).
    """
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
            f"could not parse reviewer-response JSON: {e}; raw[:200]={raw[:200]!r}",
            provider="gemini",
        ) from e
    if not isinstance(data, dict):
        raise AIError(
            "reviewer-response output is not a JSON object", provider="gemini"
        )
    comments = data.get("comments")
    if not isinstance(comments, list):
        raise AIError(
            "reviewer-response missing required `comments` list", provider="gemini"
        )
    out: list[dict[str, str]] = []
    for idx, row in enumerate(comments):
        if not isinstance(row, dict):
            raise AIError(
                f"reviewer-response comment[{idx}] is not an object",
                provider="gemini",
            )
        text = row.get("comment_text")
        resp = row.get("response_html", "")
        if not isinstance(text, str) or not text.strip():
            raise AIError(
                f"reviewer-response comment[{idx}] missing `comment_text`",
                provider="gemini",
            )
        if not isinstance(resp, str):
            raise AIError(
                f"reviewer-response comment[{idx}].response_html is not a string",
                provider="gemini",
            )
        out.append(
            {"comment_text": text.strip(), "response_html": resp.strip()}
        )
    if not out:
        raise AIError(
            "reviewer-response returned an empty comments list", provider="gemini"
        )
    return out


_ALLOWED_PEER_RECS = frozenset(
    {"reject", "major_revision", "minor_revision", "accept"}
)
_PEER_LIST_KEYS: tuple[str, ...] = (
    "strengths",
    "major_issues",
    "minor_issues",
    "methodological_concerns",
    "statistical_concerns",
    "reporting_concerns",
    "presentation_concerns",
    "references_concerns",
    "suggestions_for_improvement",
)


def _parse_peer_review_json(raw: str) -> dict[str, Any]:
    """Tolerantly parse the peer-review JSON envelope.

    Strips Markdown ```json fences. Coerces missing list keys to ``[]`` and
    missing string keys to ``""``. Validates ``recommendation`` against the
    4-level allow-list and falls back to ``"major_revision"`` if absent.
    """
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
            f"could not parse peer-review JSON: {e}; raw[:200]={raw[:200]!r}",
            provider="gemini",
        ) from e
    if not isinstance(data, dict):
        raise AIError("peer-review output is not a JSON object", provider="gemini")

    out: dict[str, Any] = {}
    impression = data.get("overall_impression")
    out["overall_impression"] = (
        impression.strip() if isinstance(impression, str) else ""
    )
    for key in _PEER_LIST_KEYS:
        raw_val = data.get(key)
        if isinstance(raw_val, list):
            out[key] = [str(x).strip() for x in raw_val if str(x).strip()]
        else:
            out[key] = []
    rec = data.get("recommendation")
    rec_norm = (
        rec.strip().lower() if isinstance(rec, str) else "major_revision"
    )
    if rec_norm not in _ALLOWED_PEER_RECS:
        rec_norm = "major_revision"
    out["recommendation"] = rec_norm
    return out


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
