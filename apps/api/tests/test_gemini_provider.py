"""Test GeminiProvider with a FakeGeminiClient — no real SDK contact."""
from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field

import pytest

from research_api.services.ai import (
    AIProviderUnavailable,
    AIRateLimited,
    AISourceInsufficient,
    GEMINI_MODEL_CHAIN,
    GeminiProvider,
)
from research_api.services.ai.gemini import ModelNotFoundError, TransientError


@dataclass
class FakeGeminiClient:
    available: list[str] = field(default_factory=lambda: list(GEMINI_MODEL_CHAIN))
    # call_handler is invoked per .generate() — can be patched per test for behavioural sequences
    call_handler: Callable[[str, str, int], str] | None = None
    calls: list[tuple[str, str]] = field(default_factory=list)
    _call_idx: int = 0

    async def list_models(self) -> list[str]:
        return list(self.available)

    async def generate(self, model: str, prompt: str) -> str:
        self.calls.append((model, prompt[:40]))
        self._call_idx += 1
        if self.call_handler is None:
            return _ok_json()
        return self.call_handler(model, prompt, self._call_idx)


def _ok_json() -> str:
    return json.dumps(
        {
            "title": "Anterior vs posterior approach in THA",
            "authors": ["John Doe", "Jane Smith"],
            "journal": "J Orthopaedic Research",
            "year": 2024,
            "volume": "42",
            "issue": "3",
            "pages": "100-110",
            "doi": "10.1234/jor.2024.0001",
            "confidence": 0.95,
        }
    )


@pytest.mark.asyncio
async def test_extract_citation_happy_path():
    client = FakeGeminiClient()
    provider = GeminiProvider(client)
    cite = await provider.extract_citation("x" * 200)
    assert cite.title.startswith("Anterior")
    assert cite.authors == ["John Doe", "Jane Smith"]
    assert cite.doi == "10.1234/jor.2024.0001"
    assert provider.active_model == "gemini-2.5-flash"


@pytest.mark.asyncio
async def test_extract_citation_resolves_chain_to_first_available():
    client = FakeGeminiClient(available=["gemini-2.0-flash", "gemini-1.5-flash-002"])
    provider = GeminiProvider(client)
    await provider.extract_citation("x" * 200)
    assert provider.active_model == "gemini-2.0-flash"


@pytest.mark.asyncio
async def test_invalid_json_raises_unavailable():
    client = FakeGeminiClient(call_handler=lambda m, p, i: "not json at all")
    provider = GeminiProvider(client)
    with pytest.raises(AIProviderUnavailable, match="parse"):
        await provider.extract_citation("x" * 200)


@pytest.mark.asyncio
async def test_tolerates_markdown_fence():
    fenced = f"```json\n{_ok_json()}\n```"
    client = FakeGeminiClient(call_handler=lambda m, p, i: fenced)
    provider = GeminiProvider(client)
    cite = await provider.extract_citation("x" * 200)
    assert cite.title.startswith("Anterior")


@pytest.mark.asyncio
async def test_transient_then_success_retries(monkeypatch):
    # Sleep instantly so the test is fast
    import research_api.services.ai.gemini as gm

    async def _noop(_):
        return None

    monkeypatch.setattr(gm.asyncio, "sleep", _noop)

    def handler(model: str, prompt: str, idx: int) -> str:
        if idx == 1:
            raise TransientError("503")
        return _ok_json()

    client = FakeGeminiClient(call_handler=handler)
    provider = GeminiProvider(client)
    cite = await provider.extract_citation("x" * 200)
    assert cite.title.startswith("Anterior")
    assert len(client.calls) == 2


@pytest.mark.asyncio
async def test_persistent_transient_raises_rate_limited(monkeypatch):
    import research_api.services.ai.gemini as gm

    async def _noop(_):
        return None

    monkeypatch.setattr(gm.asyncio, "sleep", _noop)

    def handler(model: str, prompt: str, idx: int) -> str:
        raise TransientError("429")

    client = FakeGeminiClient(call_handler=handler)
    provider = GeminiProvider(client, max_retries=3)
    with pytest.raises(AIRateLimited):
        await provider.extract_citation("x" * 200)
    assert len(client.calls) == 3


@pytest.mark.asyncio
async def test_404_demotes_and_retries_on_next_model(monkeypatch):
    import research_api.services.ai.gemini as gm

    async def _noop(_):
        return None

    monkeypatch.setattr(gm.asyncio, "sleep", _noop)

    # First model 404s, second succeeds
    def handler(model: str, prompt: str, idx: int) -> str:
        if model == "gemini-2.5-flash":
            raise ModelNotFoundError("404")
        return _ok_json()

    client = FakeGeminiClient(call_handler=handler)
    provider = GeminiProvider(client)
    cite = await provider.extract_citation("x" * 200)
    assert cite.title.startswith("Anterior")
    assert provider.active_model == "gemini-2.0-flash"


@pytest.mark.asyncio
async def test_all_models_404_raises_unavailable(monkeypatch):
    import research_api.services.ai.gemini as gm

    async def _noop(_):
        return None

    monkeypatch.setattr(gm.asyncio, "sleep", _noop)

    def handler(model: str, prompt: str, idx: int) -> str:
        raise ModelNotFoundError("404")

    client = FakeGeminiClient(call_handler=handler)
    provider = GeminiProvider(client)
    with pytest.raises(AIProviderUnavailable, match="exhausted"):
        await provider.extract_citation("x" * 200)


@pytest.mark.asyncio
async def test_short_text_raises_source_insufficient():
    client = FakeGeminiClient()
    provider = GeminiProvider(client)
    with pytest.raises(AISourceInsufficient):
        await provider.extract_citation("hi")


@pytest.mark.asyncio
async def test_summarise_happy_path():
    client = FakeGeminiClient(call_handler=lambda m, p, i: "This is a summary.")
    provider = GeminiProvider(client)
    out = await provider.summarise("x" * 100)
    assert out == "This is a summary."


@pytest.mark.asyncio
async def test_summarise_insufficient_source_signal():
    client = FakeGeminiClient(call_handler=lambda m, p, i: "INSUFFICIENT_SOURCE")
    provider = GeminiProvider(client)
    with pytest.raises(AISourceInsufficient):
        await provider.summarise("x" * 100)
