"""Meta-analysis interpretation prompt tests — citation safety contract."""
import re

from research_api.services.ai.prompts.meta_interpretation import (
    META_INTERPRETATION_PROMPT,
    build_meta_interpretation_prompt,
)


def _base_kwargs(**overrides):
    base = dict(
        metric="smd",
        model="random",
        pooled={
            "estimate": 0.45,
            "se": 0.08,
            "ci_low": 0.29,
            "ci_high": 0.61,
            "z": 5.6,
            "p": 0.0000001,
        },
        heterogeneity={
            "q": 5.4,
            "q_df": 3,
            "q_p": 0.14,
            "i2": 44.4,
            "tau2": 0.012,
        },
        studies=[
            {"article_id": "a1", "label": "Smith 2020"},
            {"article_id": "a2", "label": "Lee 2021"},
            {"article_id": "a3", "label": "Wong 2022"},
            {"article_id": "a4", "label": "Park 2023"},
        ],
        subgroups=None,
    )
    base.update(overrides)
    return base


def test_prompt_includes_pooled_numbers_verbatim():
    prompt = build_meta_interpretation_prompt(**_base_kwargs())
    assert "0.45" in prompt
    assert "0.29" in prompt
    assert "0.61" in prompt
    # The metric label is back-transformed when relevant; for SMD it's identical
    assert "standardised mean difference" in prompt.lower() or "smd" in prompt.lower()


def test_prompt_lists_every_study_token():
    prompt = build_meta_interpretation_prompt(**_base_kwargs())
    for art_id in ("a1", "a2", "a3", "a4"):
        assert f"[CITE_{art_id}]" in prompt


def test_prompt_includes_untrusted_warning():
    prompt = build_meta_interpretation_prompt(**_base_kwargs())
    # Match the explicit untrusted-data line in the prompt
    assert "untrusted" in prompt.lower()


def test_prompt_renders_subgroup_block_when_present():
    sg = {
        "RCT": {"k": 2, "estimate": 0.5, "ci_low": 0.2, "ci_high": 0.8, "i2": 12.0},
        "Cohort": {"k": 2, "estimate": 0.3, "ci_low": -0.1, "ci_high": 0.7, "i2": 0.0},
    }
    prompt = build_meta_interpretation_prompt(**_base_kwargs(subgroups=sg))
    assert "RCT" in prompt
    assert "Cohort" in prompt


def test_prompt_omits_subgroup_block_when_empty():
    prompt = build_meta_interpretation_prompt(**_base_kwargs(subgroups=None))
    # The block header is present but body should say "(none)" or similar; we check no spurious labels
    assert "RCT" not in prompt
    assert "Cohort" not in prompt


def test_prompt_back_transforms_or_to_ratio():
    import math
    kw = _base_kwargs(
        metric="or",
        pooled={
            "estimate": math.log(2.0),
            "se": 0.1,
            "ci_low": math.log(1.5),
            "ci_high": math.log(2.7),
            "z": 3.0,
            "p": 0.003,
        },
    )
    prompt = build_meta_interpretation_prompt(**kw)
    # Back-transformed pooled should show "2" (the exp(log(2)) value) on the back-transformed line
    assert re.search(r"back-transformed:\s*2\b", prompt) is not None
    assert re.search(r"1\.5", prompt) is not None


def test_prompt_template_exists():
    # smoke check that the template string is non-empty
    assert isinstance(META_INTERPRETATION_PROMPT, str)
    assert len(META_INTERPRETATION_PROMPT) > 200
