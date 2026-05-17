from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from .db.base import make_engine, make_session_factory
from .settings import Settings, get_settings


@dataclass
class Container:
    settings: Settings
    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]


_container: Container | None = None


def build_container(settings: Settings | None = None) -> Container:
    s = settings or get_settings()
    engine = make_engine(s.sqlite_url)
    factory = make_session_factory(engine)
    return Container(settings=s, engine=engine, session_factory=factory)


def get_container() -> Container:
    global _container
    if _container is None:
        _container = build_container()
    return _container


def set_container(c: Container | None) -> None:
    """Test hook to override or reset the global container."""
    global _container
    _container = c
