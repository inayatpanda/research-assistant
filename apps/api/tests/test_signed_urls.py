import time
import pytest

from research_api.services.storage import StorageRef, create_token, verify_token
from research_api.services.storage.signed_urls import TokenExpired, TokenInvalid


def test_roundtrip():
    ref = StorageRef(backend="local", key="u/a/123/x.pdf")
    tok = create_token(ref, secret="secret", ttl_seconds=60)
    verified = verify_token(tok, secret="secret")
    assert verified == ref


def test_expired_token_rejected():
    ref = StorageRef(backend="local", key="u/a/123/x.pdf")
    tok = create_token(ref, secret="secret", ttl_seconds=-1)
    # Force the small race window
    time.sleep(0.01)
    with pytest.raises(TokenExpired):
        verify_token(tok, secret="secret")


def test_tampered_token_rejected():
    ref = StorageRef(backend="local", key="u/a/123/x.pdf")
    tok = create_token(ref, secret="secret", ttl_seconds=60)
    body, sig = tok.split(".")
    # Flip a bit in the signature
    bad = body + "." + ("A" + sig[1:] if sig[0] != "A" else "B" + sig[1:])
    with pytest.raises(TokenInvalid):
        verify_token(bad, secret="secret")


def test_wrong_secret_rejected():
    ref = StorageRef(backend="local", key="u/a/123/x.pdf")
    tok = create_token(ref, secret="secret-a", ttl_seconds=60)
    with pytest.raises(TokenInvalid):
        verify_token(tok, secret="secret-b")


def test_malformed_token_rejected():
    with pytest.raises(TokenInvalid):
        verify_token("not-a-token", secret="secret")


def test_signed_payload_without_required_keys_is_invalid():
    """Regression for security fix: a signed-but-malformed payload must raise
    TokenInvalid (not KeyError or similar) so the route returns 403, not 500."""
    import base64
    import hmac
    import json
    from hashlib import sha256

    secret = "secret"
    # Sign a JSON payload that's missing the required b/k/e keys
    raw = json.dumps({"hello": "world"}).encode("utf-8")
    body = base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")
    sig = hmac.new(secret.encode(), body.encode("ascii"), sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(sig).rstrip(b"=").decode("ascii")
    token = f"{body}.{sig_b64}"
    with pytest.raises(TokenInvalid):
        verify_token(token, secret=secret)
