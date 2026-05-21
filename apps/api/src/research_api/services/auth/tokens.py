"""Phase S1 — token generation + hashing.

Sessions and invitations follow the same pattern:
* Generate a 32-byte URL-safe random token (this goes to the cookie /
  invitation URL).
* Store only its SHA-256 hash in the DB.
* When the client presents the token, hash it server-side and look up by
  hash.

This means a DB dump never leaks usable session cookies / invitation
tokens — an attacker would still need the raw token.
"""
from __future__ import annotations

import hashlib
import secrets


def generate_token(nbytes: int = 32) -> str:
    """URL-safe random token. 32 bytes → ~43 base64 chars."""
    return secrets.token_urlsafe(nbytes)


def hash_token(token: str) -> str:
    """Stable SHA-256 hex digest of the raw token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
