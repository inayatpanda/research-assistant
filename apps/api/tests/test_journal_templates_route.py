"""Phase 8.7 — GET /api/journal-templates."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_list_journal_templates_returns_catalogue(client) -> None:
    r = await client.get("/api/journal-templates")
    assert r.status_code == 200
    rows = r.json()
    assert isinstance(rows, list)
    assert len(rows) == 8
    keys = {row["key"] for row in rows}
    assert "jbjs" in keys
