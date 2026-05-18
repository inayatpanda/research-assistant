"""Phase 12 — Reviewer-response prompt builder + JSON parser unit tests."""
from __future__ import annotations

import json

import pytest

from research_api.services.ai.errors import AIError
from research_api.services.ai.gemini import _parse_reviewer_response_json
from research_api.services.ai.prompts.reviewer_response import (
    REVIEWER_RESPONSE_SYSTEM_PROMPT,
    build_reviewer_response_prompt,
)


def test_build_reviewer_response_prompt_includes_block() -> None:
    system, user = build_reviewer_response_prompt(
        raw_comments="1. Add power calc.\n\n2. Fix typo.",
        abstract="Methods: We did things.",
    )
    assert system == REVIEWER_RESPONSE_SYSTEM_PROMPT
    assert "Add power calc" in user
    assert "Fix typo" in user
    assert "Methods: We did things." in user


def test_parse_reviewer_response_json_happy_path() -> None:
    raw = json.dumps({
        "comments": [
            {"comment_text": "Add power calc.", "response_html": "<p>Done.</p>"},
            {"comment_text": "Fix typo.", "response_html": "<p>Fixed.</p>"},
        ]
    })
    out = _parse_reviewer_response_json(raw)
    assert len(out) == 2
    assert out[0]["comment_text"] == "Add power calc."
    assert out[0]["response_html"] == "<p>Done.</p>"


def test_parse_reviewer_response_json_tolerates_markdown_fence() -> None:
    raw = "```json\n" + json.dumps({
        "comments": [{"comment_text": "Hi", "response_html": ""}]
    }) + "\n```"
    out = _parse_reviewer_response_json(raw)
    assert out == [{"comment_text": "Hi", "response_html": ""}]


def test_parse_reviewer_response_json_rejects_non_object() -> None:
    with pytest.raises(AIError):
        _parse_reviewer_response_json("[1,2,3]")


def test_parse_reviewer_response_json_rejects_missing_comments() -> None:
    with pytest.raises(AIError):
        _parse_reviewer_response_json(json.dumps({"foo": "bar"}))


def test_parse_reviewer_response_json_rejects_blank_comment_text() -> None:
    raw = json.dumps({
        "comments": [{"comment_text": "  ", "response_html": "x"}]
    })
    with pytest.raises(AIError):
        _parse_reviewer_response_json(raw)


def test_parse_reviewer_response_json_rejects_empty_list() -> None:
    with pytest.raises(AIError):
        _parse_reviewer_response_json(json.dumps({"comments": []}))


def test_parse_reviewer_response_json_rejects_non_string_response() -> None:
    raw = json.dumps({
        "comments": [{"comment_text": "x", "response_html": 42}]
    })
    with pytest.raises(AIError):
        _parse_reviewer_response_json(raw)
