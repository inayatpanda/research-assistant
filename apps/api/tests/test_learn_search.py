"""Phase 5c — Cross-category Learn search regression tests."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_search_returns_hits_from_multiple_categories(client) -> None:
    """A common term like 'CI' or 'analysis' should hit several categories."""
    r = await client.get("/api/learn/search", params={"q": "PRISMA"})
    assert r.status_code == 200, r.text
    hits = r.json()
    assert isinstance(hits, list)
    assert hits, "expected at least one hit for 'PRISMA'"
    categories = {h["category"] for h in hits}
    # PRISMA shows up in checklists and is referenced in walkthroughs.
    assert "checklists" in categories
    assert "walkthroughs" in categories


@pytest.mark.asyncio
async def test_search_is_case_insensitive(client) -> None:
    lower = await client.get("/api/learn/search", params={"q": "anova"})
    upper = await client.get("/api/learn/search", params={"q": "ANOVA"})
    mixed = await client.get("/api/learn/search", params={"q": "Anova"})
    assert lower.status_code == 200
    assert upper.status_code == 200
    assert mixed.status_code == 200
    lower_slugs = {(h["category"], h["slug"]) for h in lower.json()}
    upper_slugs = {(h["category"], h["slug"]) for h in upper.json()}
    mixed_slugs = {(h["category"], h["slug"]) for h in mixed.json()}
    assert lower_slugs == upper_slugs == mixed_slugs
    assert lower_slugs, "expected non-empty results for 'anova'"
