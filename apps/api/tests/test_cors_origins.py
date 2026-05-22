"""Fix-E2E/1 — CORS allow-list regression.

Vite auto-falls-back to ports 5174/5175/… when 5173 is busy. We allow-list
the 5173-5180 band on both 127.0.0.1 and localhost so login does not break
just because the user's first dev shell is already on 5173.
"""

import pytest

from research_api.settings import Settings


def test_cors_origin_default_includes_vite_fallback_ports():
    s = Settings()
    expected = {
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:5174",
        "http://localhost:5174",
        "http://127.0.0.1:5175",
        "http://localhost:5175",
        "http://127.0.0.1:5180",
        "http://localhost:5180",
    }
    missing = expected - set(s.cors_origins)
    assert not missing, f"CORS allow-list missing entries: {missing}"


@pytest.mark.asyncio
async def test_cors_preflight_allows_vite_5174(client):
    """A real browser preflight from http://localhost:5174 must succeed.

    Reproduces HIGH-1 from the live walkthrough: Vite auto-falling-back to
    5174 broke login because CORS rejected the origin.
    """
    res = await client.options(
        "/api/auth/login",
        headers={
            "Origin": "http://localhost:5174",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert res.status_code in (200, 204)
    allow_origin = res.headers.get("access-control-allow-origin", "")
    assert allow_origin == "http://localhost:5174"


@pytest.mark.asyncio
async def test_cors_simple_response_includes_5174(client):
    """A GET with Origin: localhost:5174 must echo the origin back."""
    res = await client.get(
        "/health", headers={"Origin": "http://localhost:5174"}
    )
    assert res.status_code == 200
    assert res.headers.get("access-control-allow-origin") == "http://localhost:5174"
