"""Real Gemini SDK adapter — implements the GeminiClient port.

Kept separate from gemini.py so the provider stays testable without importing
the real SDK in tests. Errors are mapped to the provider's marker exceptions.
"""
from __future__ import annotations

import asyncio
from typing import Any

import google.generativeai as genai
from google.api_core import exceptions as gax
from google.generativeai.types import HarmBlockThreshold, HarmCategory

from .gemini import GeminiClient, ModelNotFoundError, TransientError

_BLOCK_NONE: dict[HarmCategory, HarmBlockThreshold] = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}


class RealGeminiClient(GeminiClient):
    def __init__(self, api_key: str) -> None:
        genai.configure(api_key=api_key)

    async def list_models(self) -> list[str]:
        def _list() -> list[str]:
            names: list[str] = []
            for m in genai.list_models():
                # Strip "models/" prefix the SDK emits
                short = m.name.split("/", 1)[1] if m.name.startswith("models/") else m.name
                if "generateContent" in m.supported_generation_methods:
                    names.append(short)
            return names

        try:
            return await asyncio.to_thread(_list)
        except gax.GoogleAPICallError as e:
            raise TransientError(f"list_models failed: {e}") from e

    async def generate(self, model: str, prompt: str) -> str:
        def _call() -> str:
            m = genai.GenerativeModel(model_name=model, safety_settings=_BLOCK_NONE)
            resp = m.generate_content(prompt)
            return _extract_text(resp)

        try:
            return await asyncio.to_thread(_call)
        except gax.NotFound as e:
            raise ModelNotFoundError(f"{model} not found: {e}") from e
        except gax.ResourceExhausted as e:  # 429
            raise TransientError(f"rate limited: {e}") from e
        except gax.ServiceUnavailable as e:  # 503
            raise TransientError(f"service unavailable: {e}") from e
        except gax.DeadlineExceeded as e:
            raise TransientError(f"deadline exceeded: {e}") from e
        except gax.GoogleAPICallError as e:
            # Default: treat as transient; downstream retry will handle
            raise TransientError(f"google api error: {e}") from e


def _extract_text(resp: Any) -> str:
    # google-generativeai's response wraps candidates; .text consolidates parts
    try:
        return resp.text
    except Exception:
        # Defensive: walk candidates manually
        try:
            return "".join(part.text for c in resp.candidates for part in c.content.parts)
        except Exception:
            return ""
