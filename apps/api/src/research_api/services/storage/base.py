from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class StorageRef:
    """Opaque reference to a stored file. Same shape across all FileStorage backends."""

    backend: str  # "local" | "supabase"
    key: str      # e.g. "user-a/articles/<uuid>/paper.pdf"


class FileStorage(Protocol):
    async def save(
        self, user_id: str, namespace: str, filename: str, data: bytes
    ) -> StorageRef: ...
    async def read(self, ref: StorageRef) -> bytes: ...
    async def delete(self, ref: StorageRef) -> None: ...
    async def signed_url(self, ref: StorageRef, expires_in: int = 3600) -> str: ...
