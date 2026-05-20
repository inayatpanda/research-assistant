"""Tests for the result-interpretation prompt builder and GeminiProvider.interpret_result."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import pytest

from research_api.services.ai import (
    AISourceInsufficient,
    GEMINI_MODEL_CHAIN,
    GeminiProvider,
)
from research_api.services.ai.prompts import (
    RESULT_INTERPRETATION_PROMPT,
    build_result_interpretation_prompt,
)
from research_api.services.ai.prompts.result_interpretation import _format_assumptions


SAMPLE_SUMMARY = {
    "statistic": 2.345,
    "p_value": 0.018,
    "effect_size": 0.42,
    "ci_low": 0.05,
    "ci_high": 0.79,
    "n": 120,
    "df": 118,
    "extras": {"mean_a": 3.1, "mean_b": 2.4},
}
SAMPLE_ASSUMPTIONS = {
    "shapiro": {"passed": True, "p_value": 0.21},
    "levene": {"passed": False, "p_value": 0.03, "note": "variances differ"},
}


# ----- prompt builder -------------------------------------------------------


def test_prompt_template_has_token_preservation_rule():
    assert "DO NOT CHANGE" in RESULT_INTERPRETATION_PROMPT
    assert "verbatim" in RESULT_INTERPRETATION_PROMPT
    assert "{cite_token}" in RESULT_INTERPRETATION_PROMPT


def test_prompt_includes_rounding_rules():
    text = RESULT_INTERPRETATION_PROMPT
    assert "Round p-values to 3 decimal places" in text
    assert "<0.001" in text
    assert "2-3 significant figures" in text
    assert "Round percentages to 1 decimal place" in text
    assert "scientific notation" in text


def test_prompt_forbids_dataset_author_year_wrapper():
    """The model must NOT emit `(Dataset, YYYY)` (or any author-year wrapper)
    around the citation token — the downstream citation engine formats the
    visible marker per the active style. See Fix 2 in the demo polish task."""
    text = RESULT_INTERPRETATION_PROMPT
    # The literal anti-pattern is called out by name.
    assert "(Dataset, 2026)" in text
    assert "(Dataset, YYYY)" in text
    # And the rule explicitly forbids "Dataset" appearing as an author label.
    assert 'The word "Dataset" must not appear as an author label' in text


def test_prompt_does_not_instruct_model_to_emit_dataset_author_year_form():
    """Regression: an earlier version of the prompt encouraged the model to
    use an author-year inline like `(Dataset, 2026)`. The current prompt
    must not contain any such bare directive — the only references to
    "Dataset, YYYY" are NEGATIVE examples ("do NOT wrap …")."""
    text = RESULT_INTERPRETATION_PROMPT
    # The phrase must only appear inside a negative instruction (line starts
    # with "Emit ONLY" or "Do NOT" / contains "NOT" within the same sentence).
    # We check that EVERY occurrence of "Dataset," is preceded by a negation
    # keyword somewhere on its line.
    for line in text.splitlines():
        if "Dataset," in line:
            lower = line.lower()
            assert ("not" in lower) or ("forbid" in lower) or ("only" in lower), (
                f"Unexpected positive use of 'Dataset,' author-year form: {line!r}"
            )


def test_builder_interpolates_all_key_numbers():
    prompt = build_result_interpretation_prompt(
        test_label="Independent samples t-test",
        rationale="Two independent numeric groups; normality met.",
        summary=SAMPLE_SUMMARY,
        assumptions=SAMPLE_ASSUMPTIONS,
        cite_token="[CITE_dataset_abc123]",
    )
    assert "Independent samples t-test" in prompt
    assert "Two independent numeric groups" in prompt
    assert "2.345" in prompt
    assert "0.018" in prompt
    assert "0.42" in prompt
    assert "0.05" in prompt
    assert "0.79" in prompt
    assert "120" in prompt
    assert "118" in prompt
    assert "[CITE_dataset_abc123]" in prompt
    # extras serialised as JSON inside the prompt
    assert "mean_a" in prompt


def test_builder_preserves_opaque_cite_token_unmodified():
    token = "[CITE_dataset_a-very-long_id_99]"
    prompt = build_result_interpretation_prompt(
        test_label="Mann-Whitney U",
        rationale="Skewed numeric outcome between two groups.",
        summary={"statistic": 1.0, "p_value": 0.5},
        assumptions=None,
        cite_token=token,
    )
    # Token appears exactly as given - no escaping, no truncation
    assert prompt.count(token) >= 2  # both the directive line and the rule reference


def test_builder_renders_assumptions_block_with_known_keys():
    prompt = build_result_interpretation_prompt(
        test_label="Independent samples t-test",
        rationale="Normality check required.",
        summary={"statistic": 1.0, "p_value": 0.04},
        assumptions={
            "shapiro": {"passed": True, "p_value": 0.21},
            "levene": {"passed": False, "p_value": 0.03},
            "prop_hazards": {"passed": True},
        },
        cite_token="[CITE_dataset_x]",
    )
    assert "shapiro" in prompt
    assert "levene" in prompt
    assert "prop_hazards" in prompt
    assert "FAILED" in prompt  # levene failed
    assert "passed" in prompt


def test_format_assumptions_handles_empty():
    assert "none recorded" in _format_assumptions(None)
    assert "none recorded" in _format_assumptions({})


def test_format_assumptions_handles_string_values():
    out = _format_assumptions({"note": "skipped: n too small"})
    assert "note" in out
    assert "skipped" in out


def test_builder_handles_missing_p_value():
    prompt = build_result_interpretation_prompt(
        test_label="ICC(2,1)",
        rationale="Reliability across raters.",
        summary={"statistic": 0.8, "p_value": None, "effect_size": 0.8},
        assumptions=None,
        cite_token="[CITE_dataset_x]",
    )
    # p_value missing surfaces as 'None' in the numeric block; the rule line
    # in the template instructs the model how to phrase it.
    assert "p_value = None" in prompt
    assert "p was not estimable" in prompt


# ----- GeminiProvider.interpret_result -------------------------------------


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
            return "An interpretation paragraph. [CITE_dataset_abc]"
        return self.call_handler(model, prompt, self._call_idx)


@pytest.mark.asyncio
async def test_interpret_result_routes_through_model_chain():
    captured: dict[str, str] = {}

    def handler(model: str, prompt: str, idx: int) -> str:
        captured["model"] = model
        captured["prompt"] = prompt
        return "An interpretation paragraph. [CITE_dataset_abc]"

    client = FakeGeminiClient(call_handler=handler)
    provider = GeminiProvider(client)
    out = await provider.interpret_result(
        test_label="Independent samples t-test",
        rationale="Two numeric groups; normality met.",
        summary=SAMPLE_SUMMARY,
        assumptions=SAMPLE_ASSUMPTIONS,
        cite_token="[CITE_dataset_abc]",
    )
    assert out == "An interpretation paragraph. [CITE_dataset_abc]"
    assert captured["model"] == "gemini-2.5-flash"
    # Prompt routed through builder
    assert "Independent samples t-test" in captured["prompt"]
    assert "[CITE_dataset_abc]" in captured["prompt"]
    assert "2.345" in captured["prompt"]


@pytest.mark.asyncio
async def test_interpret_result_strips_whitespace():
    client = FakeGeminiClient(
        call_handler=lambda m, p, i: "\n  Result paragraph [CITE_dataset_x].  \n"
    )
    provider = GeminiProvider(client)
    out = await provider.interpret_result(
        test_label="t-test",
        rationale="r",
        summary={"statistic": 1, "p_value": 0.05},
        assumptions=None,
        cite_token="[CITE_dataset_x]",
    )
    assert out == "Result paragraph [CITE_dataset_x]."


@pytest.mark.asyncio
async def test_interpret_result_returns_mangled_output_as_is():
    # The provider is NOT responsible for validating that the model preserved
    # the token - that contract belongs to the route layer. The provider must
    # return whatever the model produced so the route can decide.
    mangled = "The test statistic was significant. [CITE_dataset_WRONG]"

    client = FakeGeminiClient(call_handler=lambda m, p, i: mangled)
    provider = GeminiProvider(client)
    out = await provider.interpret_result(
        test_label="t-test",
        rationale="r",
        summary={"statistic": 1.0, "p_value": 0.04},
        assumptions=None,
        cite_token="[CITE_dataset_abc]",
    )
    assert out == mangled  # passed through unchanged - no validation here


@pytest.mark.asyncio
async def test_interpret_result_returns_output_when_token_dropped_entirely():
    # Same contract: even when the model omits the token, the provider does
    # not raise - the caller must check.
    dropped = "The test statistic was significant."
    client = FakeGeminiClient(call_handler=lambda m, p, i: dropped)
    provider = GeminiProvider(client)
    out = await provider.interpret_result(
        test_label="t-test",
        rationale="r",
        summary={"statistic": 1.0, "p_value": 0.04},
        assumptions=None,
        cite_token="[CITE_dataset_abc]",
    )
    assert out == dropped


@pytest.mark.asyncio
async def test_interpret_result_rejects_blank_cite_token():
    client = FakeGeminiClient()
    provider = GeminiProvider(client)
    with pytest.raises(AISourceInsufficient):
        await provider.interpret_result(
            test_label="t-test",
            rationale="r",
            summary={"statistic": 1.0, "p_value": 0.04},
            assumptions=None,
            cite_token="   ",
        )


# ----- FakeAIProvider contract used by integration tests -------------------


@pytest.mark.asyncio
async def test_fake_ai_provider_interpret_result_deterministic():
    from tests.conftest import FakeAIProvider

    fake = FakeAIProvider()
    out = await fake.interpret_result(
        test_label="Independent samples t-test",
        rationale="Two numeric groups.",
        summary={"statistic": 2.5, "p_value": 0.012},
        assumptions=None,
        cite_token="[CITE_dataset_42]",
    )
    assert "Independent samples t-test" in out
    assert "statistic=2.5" in out
    assert "p=0.012" in out
    assert "[CITE_dataset_42]" in out
    assert "interpret_result" in fake.calls
