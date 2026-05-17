import pytest


@pytest.mark.asyncio
async def test_serve_file_with_valid_token(client, tmp_path):
    """Upload a file via storage, get a signed URL, fetch it through /files/{token}."""
    from research_api.container import get_container

    container = get_container()
    ref = await container.storage.save("local-user", "articles", "x.pdf", b"%PDF-1.4 fake")
    url = await container.storage.signed_url(ref, expires_in=60)
    # URL is /files/{token}; httpx client base_url is http://test, so we just GET the path
    r = await client.get(url)
    assert r.status_code == 200
    assert r.content == b"%PDF-1.4 fake"


@pytest.mark.asyncio
async def test_serve_file_with_expired_token(client):
    from research_api.container import get_container
    from research_api.services.storage import StorageRef
    from research_api.services.storage.signed_urls import create_token

    container = get_container()
    ref = StorageRef(backend="local", key="local-user/articles/abc/x.pdf")
    expired = create_token(ref, secret=container.settings.api_signing_secret, ttl_seconds=-1)
    r = await client.get(f"/files/{expired}")
    assert r.status_code == 410


@pytest.mark.asyncio
async def test_serve_file_with_tampered_token(client):
    from research_api.container import get_container
    from research_api.services.storage import StorageRef
    from research_api.services.storage.signed_urls import create_token

    container = get_container()
    ref = StorageRef(backend="local", key="local-user/articles/abc/x.pdf")
    tok = create_token(ref, secret=container.settings.api_signing_secret, ttl_seconds=60)
    body, sig = tok.split(".")
    bad = body + "." + ("A" + sig[1:] if sig[0] != "A" else "B" + sig[1:])
    r = await client.get(f"/files/{bad}")
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_serve_file_missing_returns_404(client):
    from research_api.container import get_container
    from research_api.services.storage import StorageRef
    from research_api.services.storage.signed_urls import create_token

    container = get_container()
    ref = StorageRef(backend="local", key="local-user/articles/abc/nonexistent.pdf")
    tok = create_token(ref, secret=container.settings.api_signing_secret, ttl_seconds=60)
    r = await client.get(f"/files/{tok}")
    assert r.status_code == 404
