import pytest

from research_api.services.ai import AIProviderUnavailable, ModelChain


def test_resolve_picks_first_available():
    chain = ModelChain.resolve(
        available={"gemini-2.0-flash", "gemini-1.5-flash-latest"},
        chain=("gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash-latest"),
        provider="gemini",
    )
    assert chain.active == "gemini-2.0-flash"


def test_resolve_picks_head_when_present():
    chain = ModelChain.resolve(
        available={"gemini-2.5-flash", "gemini-2.0-flash"},
        chain=("gemini-2.5-flash", "gemini-2.0-flash"),
        provider="gemini",
    )
    assert chain.active == "gemini-2.5-flash"


def test_resolve_raises_when_none_available():
    with pytest.raises(AIProviderUnavailable, match="no model"):
        ModelChain.resolve(
            available={"some-other-model"},
            chain=("gemini-2.5-flash", "gemini-2.0-flash"),
            provider="gemini",
        )


def test_demote_promotes_next():
    chain = ModelChain.resolve(
        available={"gemini-2.5-flash", "gemini-2.0-flash"},
        chain=("gemini-2.5-flash", "gemini-2.0-flash"),
        provider="gemini",
    )
    demoted = chain.demote()
    assert demoted.active == "gemini-2.0-flash"
    assert "gemini-2.5-flash" not in demoted.chain


def test_demote_exhaustion_raises():
    chain = ModelChain.resolve(
        available={"gemini-2.5-flash"},
        chain=("gemini-2.5-flash",),
        provider="gemini",
    )
    with pytest.raises(AIProviderUnavailable, match="exhausted"):
        chain.demote()
