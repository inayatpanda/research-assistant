"""Phase S1 — argon2id password hashing.

Wraps argon2-cffi with sensible defaults. Hashes are
self-describing (the algorithm/params are encoded in the hash string), so
upgrading the parameters later doesn't break existing rows.

Defaults: time_cost=2, memory_cost=65536 (64 MiB), parallelism=2. These
balance security and the latency the user feels on a 2017-era laptop.
"""
from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHash, VerificationError, VerifyMismatchError

_hasher = PasswordHasher(
    time_cost=2,
    memory_cost=65536,
    parallelism=2,
    hash_len=32,
    salt_len=16,
)


def hash_password(plain: str) -> str:
    """Return an argon2id encoded hash for ``plain``."""
    return _hasher.hash(plain)


def verify_password(plain: str, encoded: str) -> bool:
    """Return ``True`` iff ``plain`` verifies against ``encoded``.

    A genuinely empty stored hash (e.g. the legacy placeholder user that
    cannot be logged into) always returns False. Any malformed hash also
    returns False — never raises.
    """
    if not encoded:
        return False
    try:
        return _hasher.verify(encoded, plain)
    except (VerifyMismatchError, VerificationError, InvalidHash):
        return False
    except Exception:
        return False


def needs_rehash(encoded: str) -> bool:
    """Whether the encoded hash should be regenerated with current params."""
    if not encoded:
        return False
    try:
        return _hasher.check_needs_rehash(encoded)
    except Exception:
        return False
