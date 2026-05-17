from fastapi import APIRouter, Depends
from sqlalchemy import text

from ..container import Container, get_container
from ..schemas.health import HealthResponse, ProviderStatus

router = APIRouter(tags=["meta"])


async def _check_db(container: Container) -> bool:
    try:
        async with container.engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def _check_providers(container: Container) -> dict[str, ProviderStatus]:
    s = container.settings
    return {
        "gemini": (
            ProviderStatus(ok=True, active_model=None)
            if s.gemini_api_key
            else ProviderStatus(ok=False, reason="no key")
        ),
        "claude": (
            ProviderStatus(ok=True)
            if s.claude_api_key
            else ProviderStatus(ok=False, reason="no key")
        ),
        "openai": (
            ProviderStatus(ok=True)
            if s.openai_api_key
            else ProviderStatus(ok=False, reason="no key")
        ),
    }


@router.get("/health", response_model=HealthResponse)
async def health(container: Container = Depends(get_container)) -> HealthResponse:
    db_ok = await _check_db(container)
    providers = _check_providers(container)
    any_ai_ok = any(p.ok for p in providers.values())
    if db_ok and any_ai_ok:
        status: str = "ok"
    elif db_ok:
        status = "degraded"
    else:
        status = "down"
    return HealthResponse(
        status=status,  # type: ignore[arg-type]
        version="0.0.1",
        db_ok=db_ok,
        storage_backend=container.settings.storage_backend,
        ai_providers=providers,
    )
