"""Fix-E2E/7 — /api/health alias regression.

Mobile-shell and desktop-bridge clients ping ``/api/health`` because every
other route in the product lives under ``/api/*``. Without this alias the
health badge in the UI lit up red even though the API was healthy.
"""

import pytest


@pytest.mark.asyncio
async def test_health_at_root_path(client):
    res = await client.get("/health")
    assert res.status_code == 200
    payload = res.json()
    assert "status" in payload
    assert payload.get("db_ok") is True


@pytest.mark.asyncio
async def test_health_at_api_prefix_alias(client):
    """``/api/health`` must return the same shape as ``/health``."""
    res = await client.get("/api/health")
    assert res.status_code == 200
    payload = res.json()
    assert "status" in payload
    assert payload.get("db_ok") is True
    # Same set of top-level keys as the non-prefixed route.
    assert set(payload.keys()) >= {
        "status",
        "version",
        "db_ok",
        "storage_backend",
        "ai_providers",
    }
