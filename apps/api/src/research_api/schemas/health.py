from typing import Literal

from pydantic import BaseModel


class ProviderStatus(BaseModel):
    ok: bool
    active_model: str | None = None
    reason: str | None = None


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded", "down"]
    version: str
    db_ok: bool
    storage_backend: str
    ai_providers: dict[str, ProviderStatus]
