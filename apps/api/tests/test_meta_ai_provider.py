"""AIProvider.interpret_meta_analysis — Gemini + FakeAI + Unconfigured."""
from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field

import pytest

from research_api.services.ai import (
    AIProviderUnavailable,
    AISourceInsufficient,
    GEMINI_MODEL_CHAIN,
    GeminiProvider,
)
from research_api.services.ai.unconfigured import UnconfiguredAIProvider


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
            return "Pooled effect is meaningful [CITE_a1] [CITE_a2]."
        return self.call_handler(model, prompt, self._call_idx)


def _kwargs(**overrides):
    base = dict(
        metric="smd",
        model="random",
        pooled={"estimate": 0.45, "se": 0.08, "ci_low": 0.29, "ci_high": 0.61, "z": 5.6, "p": 0.0001},
        heterogeneity={"q": 5.4, "q_df": 3, "q_p": 0.14, "i2": 44.4, "tau2": 0.012},
        studies=[
            {"article_id": "a1", "label": "Smith 2020"},
            {"article_id": "a2", "label": "Lee 2021"},
        ],
        subgroups=None,
    )
    base.update(overrides)
    return base


@pytest.mark.asyncio
async def test_gemini_interpret_meta_returns_string():
    client = FakeGeminiClient()
    provider = GeminiProvider(client)
    prose = await provider.interpret_meta_analysis(**_kwargs())
    assert isinstance(prose, str)
    assert "[CITE_a1]" in prose


@pytest.mark.asyncio
async def test_gemini_raises_on_empty_studies():
    client = FakeGeminiClient()
    provider = GeminiProvider(client)
    with pytest.raises(AISourceInsufficient):
        await provider.interpret_meta_analysis(**_kwargs(studies=[]))


@pytest.mark.asyncio
async def test_gemini_raises_on_missing_estimate():
    client = FakeGeminiClient()
    provider = GeminiProvider(client)
    with pytest.raises(AISourceInsufficient):
        await provider.interpret_meta_analysis(**_kwargs(pooled={"estimate": None}))


@pytest.mark.asyncio
async def test_fake_ai_returns_tokens_for_every_study():
    from tests.conftest import FakeAIProvider
    fake = FakeAIProvider()
    prose = await fake.interpret_meta_analysis(**_kwargs())
    assert "[CITE_a1]" in prose
    assert "[CITE_a2]" in prose


@pytest.mark.asyncio
async def test_unconfigured_raises():
    provider = UnconfiguredAIProvider()
    with pytest.raises(AIProviderUnavailable):
        await provider.interpret_meta_analysis(**_kwargs())


@pytest.mark.asyncio
async def test_prompt_never_invents_cite_token():
    """Regex over the FakeAI prose: every [CITE_xxx] is in `studies`."""
    from tests.conftest import FakeAIProvider
    fake = FakeAIProvider()
    prose = await fake.interpret_meta_analysis(**_kwargs())
    tokens = re.findall(r"\[CITE_([^\]]+)\]", prose)
    allowed = {"a1", "a2"}
    assert set(tokens) <= allowed
