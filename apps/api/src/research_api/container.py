from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from .db.base import make_engine, make_session_factory
from .services.ai import AIProvider, GeminiProvider, UnconfiguredAIProvider
from .services.storage import FileStorage, LocalFsStorage
from .settings import Settings, get_settings


@dataclass
class Container:
    settings: Settings
    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]
    storage: FileStorage
    ai: AIProvider


_container: Container | None = None


def _build_ai(settings: Settings) -> AIProvider:
    """Construct the configured AI provider. Returns Unconfigured stub if no key."""
    name = settings.ai_provider_default
    if name == "gemini":
        if not settings.gemini_api_key:
            return UnconfiguredAIProvider(name="gemini")
        # Lazy import — avoids pulling the SDK during tests that override the container.
        from .services.ai.real_gemini_client import RealGeminiClient

        return GeminiProvider(RealGeminiClient(settings.gemini_api_key))
    # Claude / OpenAI providers land in later phases — return Unconfigured for now.
    return UnconfiguredAIProvider(name=name)


def build_container(
    settings: Settings | None = None,
    *,
    storage: FileStorage | None = None,
    ai: AIProvider | None = None,
) -> Container:
    """Construct the container. Test hooks: pass `storage=` or `ai=` to substitute fakes."""
    s = settings or get_settings()
    engine = make_engine(s.sqlite_url)
    factory = make_session_factory(engine)
    return Container(
        settings=s,
        engine=engine,
        session_factory=factory,
        storage=storage
        or LocalFsStorage(root=s.data_dir, signing_secret=s.api_signing_secret),
        ai=ai or _build_ai(s),
    )


def get_container() -> Container:
    global _container
    if _container is None:
        _container = build_container()
    return _container


def set_container(c: Container | None) -> None:
    """Test hook to override or reset the global container."""
    global _container
    _container = c
