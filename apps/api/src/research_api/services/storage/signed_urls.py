"""HMAC-signed, expiring URL tokens for serving stored files."""
from __future__ import annotations

import base64
import hmac
import json
import time
from dataclasses import dataclass
from hashlib import sha256

from .base import StorageRef


class TokenError(Exception):
    pass


class TokenExpired(TokenError):
    pass


class TokenInvalid(TokenError):
    pass


@dataclass(frozen=True)
class TokenPayload:
    backend: str
    key: str
    exp: int  # unix seconds


def _b64u(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode("ascii")


def _b64u_decode(s: str) -> bytes:
    pad = (-len(s)) % 4
    return base64.urlsafe_b64decode(s + ("=" * pad))


def create_token(ref: StorageRef, *, secret: str, ttl_seconds: int = 3600) -> str:
    payload = TokenPayload(backend=ref.backend, key=ref.key, exp=int(time.time()) + ttl_seconds)
    raw = json.dumps({"b": payload.backend, "k": payload.key, "e": payload.exp}).encode("utf-8")
    body = _b64u(raw)
    sig = hmac.new(secret.encode("utf-8"), body.encode("ascii"), sha256).digest()
    return f"{body}.{_b64u(sig)}"


def verify_token(token: str, *, secret: str) -> StorageRef:
    try:
        body, sig_b64 = token.split(".", 1)
    except ValueError as e:
        raise TokenInvalid("malformed token") from e
    expected = hmac.new(secret.encode("utf-8"), body.encode("ascii"), sha256).digest()
    try:
        provided = _b64u_decode(sig_b64)
    except Exception as e:
        raise TokenInvalid("bad signature encoding") from e
    if not hmac.compare_digest(expected, provided):
        raise TokenInvalid("signature mismatch")
    try:
        raw = json.loads(_b64u_decode(body).decode("utf-8"))
    except Exception as e:
        raise TokenInvalid("bad payload encoding") from e
    # Validate required keys explicitly — a signed-but-malformed payload should
    # be a clean TokenInvalid, not a server-side KeyError.
    try:
        backend = str(raw["b"])
        key = str(raw["k"])
        exp = int(raw["e"])
    except (KeyError, ValueError, TypeError) as e:
        raise TokenInvalid("missing or invalid payload fields") from e
    if exp < int(time.time()):
        raise TokenExpired("token expired")
    return StorageRef(backend=backend, key=key)
