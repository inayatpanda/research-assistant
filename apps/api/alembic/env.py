import os
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool

from alembic import context

from research_api.db.base import Base
from research_api.db import models  # noqa: F401  ensure model import

config = context.config

# Resolve DB path to an absolute path under the repo root: <repo>/data/research.db
# alembic.ini's relative path is brittle depending on where alembic is invoked from.
# __file__ = apps/api/alembic/env.py
#   parents[0] = apps/api/alembic
#   parents[1] = apps/api
#   parents[2] = apps
#   parents[3] = repo root
_repo_root = Path(__file__).resolve().parents[3]
_data_dir = _repo_root / "data"

# DEMO-FIX-D HIGH-1 — allow callers (e.g. the FastAPI lifespan auto-migrate
# step, plus tests pointing at a tmp DB) to override the alembic target URL
# via either the Config object (set BEFORE calling command.upgrade) or the
# ``ALEMBIC_SQLALCHEMY_URL`` env var. Falls back to the canonical repo path.
_explicit_url = config.get_main_option("sqlalchemy.url")
_env_url = os.environ.get("ALEMBIC_SQLALCHEMY_URL")
if _env_url:
    config.set_main_option("sqlalchemy.url", _env_url)
elif (
    not _explicit_url
    or _explicit_url.startswith("sqlite:///../")
    or _explicit_url == "sqlite:///./data/research.db"
):
    # Only fall back to the canonical repo DB when no caller-supplied URL is
    # configured. This preserves the previous default behaviour for plain
    # ``alembic upgrade head`` invocations from the apps/api directory.
    _data_dir.mkdir(parents=True, exist_ok=True)
    config.set_main_option(
        "sqlalchemy.url", f"sqlite:///{_data_dir / 'research.db'}"
    )

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
