from __future__ import annotations

import asyncio
import re
from pathlib import Path
from uuid import uuid4

from .base import FileStorage, StorageRef
from .signed_urls import create_token

_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def _normalise_filename(filename: str) -> str:
    # Reject any path components — only the basename survives. Then strip unsafe chars.
    base = Path(filename).name or "file"
    cleaned = _SAFE_NAME_RE.sub("_", base).strip("._-") or "file"
    # Cap length to avoid pathological inputs
    return cleaned[:200]


class LocalFsStorage(FileStorage):
    def __init__(self, root: Path, *, signing_secret: str, url_prefix: str = "/files") -> None:
        self.root = Path(root)
        self.signing_secret = signing_secret
        self.url_prefix = url_prefix.rstrip("/")
        (self.root / "files").mkdir(parents=True, exist_ok=True)

    def _abs_path(self, key: str) -> Path:
        # Defensive: forbid traversal in keys themselves
        p = (self.root / "files" / key).resolve()
        base = (self.root / "files").resolve()
        if not str(p).startswith(str(base)):
            raise ValueError("path traversal detected in key")
        return p

    async def save(
        self, user_id: str, namespace: str, filename: str, data: bytes
    ) -> StorageRef:
        safe_user = _SAFE_NAME_RE.sub("_", user_id) or "anon"
        safe_ns = _SAFE_NAME_RE.sub("_", namespace) or "default"
        safe_name = _normalise_filename(filename)
        key = f"{safe_user}/{safe_ns}/{uuid4().hex}/{safe_name}"
        path = self._abs_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)

        def _write() -> None:
            path.write_bytes(data)

        await asyncio.to_thread(_write)
        return StorageRef(backend="local", key=key)

    async def read(self, ref: StorageRef) -> bytes:
        if ref.backend != "local":
            raise ValueError(f"LocalFsStorage cannot read ref with backend={ref.backend}")
        path = self._abs_path(ref.key)
        return await asyncio.to_thread(path.read_bytes)

    async def delete(self, ref: StorageRef) -> None:
        if ref.backend != "local":
            return
        path = self._abs_path(ref.key)

        def _del() -> None:
            try:
                path.unlink()
            except FileNotFoundError:
                pass

        await asyncio.to_thread(_del)

    async def signed_url(self, ref: StorageRef, expires_in: int = 3600) -> str:
        token = create_token(ref, secret=self.signing_secret, ttl_seconds=expires_in)
        return f"{self.url_prefix}/{token}"
