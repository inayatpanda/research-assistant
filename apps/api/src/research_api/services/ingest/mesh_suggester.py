"""PICO-driven MeSH suggester (Phase 19 / MP19).

Given a review's PICO free-text, compose a single ``esearch db=mesh``
query (OR'd across non-empty PICO fragments) and return the top-N
descriptors.

Each PICO fragment becomes a parenthesised quoted phrase to avoid the
NCBI parser collapsing common stop-words. Whitespace-only / None
fragments are skipped silently.
"""
from __future__ import annotations

import re
from typing import Mapping

from .mesh import MeshDescriptor, search_mesh

_QUOTE_NEEDED = re.compile(r"\s")


def compose_pico_term(pico: Mapping[str, str | None]) -> str:
    """Compose a MeSH-friendly esearch ``term=`` query from a PICO dict.

    Pure function — exported so tests can pin the exact composition.
    """
    parts: list[str] = []
    for key in ("population", "intervention", "comparator", "outcome"):
        raw = (pico.get(key) or "").strip()
        if not raw:
            continue
        # If the fragment carries whitespace, wrap in quotes for the
        # NCBI parser; otherwise pass through as-is.
        if _QUOTE_NEEDED.search(raw):
            parts.append(f'"{raw}"')
        else:
            parts.append(raw)
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    return " OR ".join(parts)


async def suggest_mesh_from_pico(
    pico: Mapping[str, str | None],
    *,
    retmax: int = 10,
    api_key: str | None = None,
    http_client=None,
) -> list[MeshDescriptor]:
    """Suggest top MeSH descriptors for a review's PICO."""
    term = compose_pico_term(pico)
    if not term:
        return []
    return await search_mesh(
        term, retmax=retmax, api_key=api_key, http_client=http_client
    )


__all__ = ["compose_pico_term", "suggest_mesh_from_pico"]
