"""Tests for the screening-suggestion prompt builder and GeminiProvider.suggest_screening."""
from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field

import pytest

from research_api.services.ai import (
    AIError,
    AISourceInsufficient,
    GEMINI_MODEL_CHAIN,
    GeminiProvider,
)
from research_api.services.ai.prompts import (
    SCREENING_SUGGESTION_SYSTEM_PROMPT,
    SCREENING_SUGGESTION_USER_PROMPT,
    build_screening_suggestion_prompt,
)


PICO_SAMPLE = {
    "population": "Adults with knee osteoarthritis",
    "intervention": "Total knee arthroplasty",
    "comparator": "Conservative management",
    "outcome": "WOMAC score at 12 months",
}


# ----- prompt builder -------------------------------------------------------


def test_system_prompt_contains_non_negotiable_rules():
    assert "JSON" in SCREENING_SUGGESTION_SYSTEM_PROMPT
    assert "include" in SCREENING_SUGGESTION_SYSTEM_PROMPT
    assert "exclude" in SCREENING_SUGGESTION_SYSTEM_PROMPT
    assert "maybe" in SCREENING_SUGGESTION_SYSTEM_PROMPT
    assert "240" in SCREENING_SUGGESTION_SYSTEM_PROMPT
    assert "ADVISORY" in SCREENING_SUGGESTION_SYSTEM_PROMPT
    assert "UNTRUSTED" in SCREENING_SUGGESTION_SYSTEM_PROMPT
    # No citation token contract for screening
    assert "[CITE_" not in SCREENING_SUGGESTION_USER_PROMPT


def test_builder_interpolates_all_fields():
    system, user = build_screening_suggestion_prompt(
        eligibility_inclusion="RCTs of adult patients",
        eligibility_exclusion="Animal studies, case reports",
        pico=PICO_SAMPLE,
        article_title="A randomised trial of TKA vs physio in knee OA",
        article_abstract="We enrolled 200 adults...",
    )
    assert system == SCREENING_SUGGESTION_SYSTEM_PROMPT
    assert "RCTs of adult patients" in user
    assert "Animal studies, case reports" in user
    assert "Adults with knee osteoarthritis" in user
    assert "Total knee arthroplasty" in user
    assert "Conservative management" in user
    assert "WOMAC score at 12 months" in user
    assert "A randomised trial of TKA vs physio in knee OA" in user
    assert "We enrolled 200 adults..." in user


def test_builder_handles_empty_abstract():
    system, user = build_screening_suggestion_prompt(
        eligibility_inclusion="Adults",
        eligibility_exclusion=None,
        pico={"population": None, "intervention": None, "comparator": None, "outcome": None},
        article_title="A title-only record",
        article_abstract="",
    )
    # Builder doesn't crash and produces a coherent user prompt
    assert "A title-only record" in user
    assert "(no abstract provided)" in user
    assert "(not specified)" in user
    assert system == SCREENING_SUGGESTION_SYSTEM_PROMPT


def test_builder_handles_none_abstract():
    _, user = build_screening_suggestion_prompt(
        eligibility_inclusion=None,
        eligibility_exclusion=None,
        pico={},
        article_title="Just a title",
        article_abstract=None,
    )
    assert "Just a title" in user
    assert "(no abstract provided)" in user


def test_builder_truncates_oversized_inputs():
    huge_inclusion = "A" * 5000
    huge_abstract = "B" * 10000
    _, user = build_screening_suggestion_prompt(
        eligibility_inclusion=huge_inclusion,
        eligibility_exclusion=None,
        pico=PICO_SAMPLE,
        article_title="X",
        article_abstract=huge_abstract,
    )
    assert "A" * 2000 in user
    assert "A" * 2001 not in user
    assert "B" * 4000 in user
    assert "B" * 4001 not in user


# ----- GeminiProvider.suggest_screening ------------------------------------


@dataclass
class FakeGeminiClient:
    available: list[str] = field(default_factory=lambda: list(GEMINI_MODEL_CHAIN))
    call_handler: Callable[[str, str, int], str] | None = None
    calls: list[tuple[str, str]] = field(default_factory=list)
    _call_idx: int = 0

    async def list_models(self) -> list[str]:
        return list(self.available)

    async def generate(self, model: str, prompt: str) -> str:
        self.calls.append((model, prompt))
        self._call_idx += 1
        if self.call_handler is None:
            return json.dumps({"vote": "include", "reason": "Matches inclusion criteria."})
        return self.call_handler(model, prompt, self._call_idx)


@pytest.mark.asyncio
async def test_suggest_screening_routes_through_model_chain():
    captured: dict[str, str] = {}

    def handler(model: str, prompt: str, idx: int) -> str:
        captured["model"] = model
        captured["prompt"] = prompt
        return json.dumps({"vote": "maybe", "reason": "Ambiguous abstract."})

    client = FakeGeminiClient(call_handler=handler)
    provider = GeminiProvider(client)
    out = await provider.suggest_screening(
        eligibility_inclusion="Adults with knee OA",
        eligibility_exclusion="Paediatric studies",
        pico=PICO_SAMPLE,
        article_title="A trial of knee replacement",
        article_abstract="200 adult patients...",
    )
    assert out == {"vote": "maybe", "reason": "Ambiguous abstract.", "model": "gemini-2.5-flash"}
    assert captured["model"] == "gemini-2.5-flash"
    assert "Adults with knee OA" in captured["prompt"]
    assert "A trial of knee replacement" in captured["prompt"]
    assert "Total knee arthroplasty" in captured["prompt"]


@pytest.mark.asyncio
async def test_suggest_screening_tolerates_markdown_fence():
    fenced = "```json\n" + json.dumps({"vote": "exclude", "reason": "Off-topic."}) + "\n```"
    client = FakeGeminiClient(call_handler=lambda m, p, i: fenced)
    provider = GeminiProvider(client)
    out = await provider.suggest_screening(
        eligibility_inclusion="x",
        eligibility_exclusion="y",
        pico=PICO_SAMPLE,
        article_title="t",
        article_abstract="a",
    )
    assert out["vote"] == "exclude"
    assert out["reason"] == "Off-topic."


@pytest.mark.asyncio
async def test_suggest_screening_raises_on_malformed_json():
    client = FakeGeminiClient(call_handler=lambda m, p, i: "not json at all")
    provider = GeminiProvider(client)
    with pytest.raises(AIError, match="parse"):
        await provider.suggest_screening(
            eligibility_inclusion="x",
            eligibility_exclusion="y",
            pico=PICO_SAMPLE,
            article_title="t",
            article_abstract="a",
        )


@pytest.mark.asyncio
async def test_suggest_screening_raises_on_missing_keys():
    client = FakeGeminiClient(call_handler=lambda m, p, i: json.dumps({"vote": "include"}))
    provider = GeminiProvider(client)
    with pytest.raises(AIError, match="required keys"):
        await provider.suggest_screening(
            eligibility_inclusion="x",
            eligibility_exclusion="y",
            pico=PICO_SAMPLE,
            article_title="t",
            article_abstract="a",
        )


@pytest.mark.asyncio
async def test_suggest_screening_raises_on_invalid_vote():
    bad = json.dumps({"vote": "definitely", "reason": "bad vote value"})
    client = FakeGeminiClient(call_handler=lambda m, p, i: bad)
    provider = GeminiProvider(client)
    with pytest.raises(AIError, match="not in"):
        await provider.suggest_screening(
            eligibility_inclusion="x",
            eligibility_exclusion="y",
            pico=PICO_SAMPLE,
            article_title="t",
            article_abstract="a",
        )


@pytest.mark.asyncio
async def test_suggest_screening_normalises_vote_case():
    raw = json.dumps({"vote": "  INCLUDE  ", "reason": "  meets criteria  "})
    client = FakeGeminiClient(call_handler=lambda m, p, i: raw)
    provider = GeminiProvider(client)
    out = await provider.suggest_screening(
        eligibility_inclusion="x",
        eligibility_exclusion="y",
        pico=PICO_SAMPLE,
        article_title="t",
        article_abstract="a",
    )
    assert out["vote"] == "include"
    assert out["reason"] == "meets criteria"


@pytest.mark.asyncio
async def test_suggest_screening_accepts_empty_abstract():
    client = FakeGeminiClient(
        call_handler=lambda m, p, i: json.dumps(
            {"vote": "maybe", "reason": "insufficient information from title alone"}
        )
    )
    provider = GeminiProvider(client)
    out = await provider.suggest_screening(
        eligibility_inclusion="x",
        eligibility_exclusion="y",
        pico=PICO_SAMPLE,
        article_title="Only a title here",
        article_abstract="",
    )
    assert out["vote"] == "maybe"


@pytest.mark.asyncio
async def test_suggest_screening_rejects_blank_title():
    client = FakeGeminiClient()
    provider = GeminiProvider(client)
    with pytest.raises(AISourceInsufficient):
        await provider.suggest_screening(
            eligibility_inclusion="x",
            eligibility_exclusion="y",
            pico=PICO_SAMPLE,
            article_title="   ",
            article_abstract="some abstract",
        )


# ----- FakeAIProvider contract used by integration tests -------------------


@pytest.mark.asyncio
async def test_fake_ai_suggest_screening_deterministic():
    from tests.conftest import FakeAIProvider

    fake = FakeAIProvider()
    out = await fake.suggest_screening(
        eligibility_inclusion="x",
        eligibility_exclusion="y",
        pico=PICO_SAMPLE,
        article_title="An article",
        article_abstract="An abstract",
    )
    assert out == {
        "vote": "maybe",
        "reason": "fake-ai screening reason",
        "model": "fake-model",
    }
    assert "suggest_screening" in fake.calls


@pytest.mark.asyncio
async def test_unconfigured_provider_raises():
    from research_api.services.ai import AIProviderUnavailable, UnconfiguredAIProvider

    provider = UnconfiguredAIProvider()
    with pytest.raises(AIProviderUnavailable):
        await provider.suggest_screening(
            eligibility_inclusion="x",
            eligibility_exclusion="y",
            pico=PICO_SAMPLE,
            article_title="t",
            article_abstract="a",
        )
