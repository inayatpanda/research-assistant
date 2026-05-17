import pytest


@pytest.mark.asyncio
async def test_health_returns_200_with_provider_status(client):
    r = await client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] in {"ok", "degraded"}
    assert body["db_ok"] is True
    assert body["storage_backend"] == "local"
    assert "gemini" in body["ai_providers"]
    assert body["ai_providers"]["gemini"]["ok"] is True
    assert body["version"]
