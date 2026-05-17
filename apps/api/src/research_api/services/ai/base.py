from __future__ import annotations

from typing import Literal, Protocol

from .schemas import CitationMetadata

WritingAction = Literal["improve", "shorten", "formalise", "add_transition"]


class AIProvider(Protocol):
    """Vendor-neutral interface. Concrete implementations: GeminiProvider, ClaudeProvider, OpenAIProvider."""

    @property
    def name(self) -> str: ...

    @property
    def active_model(self) -> str | None: ...

    async def extract_citation(self, pdf_text: str) -> CitationMetadata: ...

    async def summarise(self, text: str, max_sentences: int = 2) -> str: ...

    # The remaining methods land in their respective phases (4, 5, 6, 8).
    # Included here so swap-time signature is stable.
    async def generate_draft(self, ctx: dict) -> str: ...
    async def interpret_result(self, test: str, output: dict) -> str: ...
    async def assist_writing(self, text: str, action: WritingAction) -> str: ...
