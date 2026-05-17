from fastapi import APIRouter, Depends
from sqlalchemy import text

from ..container import Container, get_container
from ..schemas.health import HealthResponse, ProviderStatus
from ..services.ai import AIProviderUnavailable
from ..services.ai.unconfigured import UnconfiguredAIProvider

router = APIRouter(tags=["meta"])


async def _check_db(container: Container) -> bool:
    try:
        async with container.engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def _probe_active_provider(container: Container) -> ProviderStatus:
    ai = container.ai
    if isinstance(ai, UnconfiguredAIProvider):
        return ProviderStatus(ok=False, reason="no key")
    # Trigger lazy chain resolution if the provider supports it (Gemini does)
    if hasattr(ai, "_ensure_chain"):
        try:
            await ai._ensure_chain()  # type: ignore[attr-defined]
        except AIProviderUnavailable as e:
            return ProviderStatus(ok=False, reason=str(e))
        except Exception as e:
            return ProviderStatus(ok=False, reason=f"probe failed: {e}")
    return ProviderStatus(ok=True, active_model=ai.active_model)


def _key_present(settings, name: str) -> bool:
    return bool(getattr(settings, f"{name}_api_key", None))


async def _check_providers(container: Container) -> dict[str, ProviderStatus]:
    s = container.settings
    default = s.ai_provider_default
    active = await _probe_active_provider(container)

    out: dict[str, ProviderStatus] = {}
    for name in ("gemini", "claude", "openai"):
        if name == default:
            out[name] = active
        elif _key_present(s, name):
            out[name] = ProviderStatus(ok=True)
        else:
            out[name] = ProviderStatus(ok=False, reason="no key")
    return out


@router.get("/health", response_model=HealthResponse)
async def health(container: Container = Depends(get_container)) -> HealthResponse:
    db_ok = await _check_db(container)
    providers = await _check_providers(container)
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
