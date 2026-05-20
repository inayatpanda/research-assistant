"""DEMO-FIX-D HIGH-1 — FastAPI lifespan auto-applies alembic migrations.

The live API used to boot against whatever schema was already on disk, so a
new ORM column added in migration 0022 (``dataset_variables.display_label``)
would 500 every ``GET /datasets`` call until the operator manually ran
``alembic upgrade head``. The browser then mis-reported the 500-without-CORS
as a CORS error.

These tests verify:
  (a) lifespan startup runs ``alembic upgrade head`` against the configured
      SQLite URL, leaving a fresh DB at the head revision with all 22+
      migration tables present.
  (b) 500-class responses carry CORS headers so the browser surfaces the
      real error.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, inspect

from research_api.main import _run_alembic_upgrade_head


API_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.asyncio
async def test_run_alembic_upgrade_head_against_fresh_db(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Calling the helper directly against an empty SQLite file ends at head."""
    db_file = tmp_path / "fresh.db"
    async_url = f"sqlite+aiosqlite:///{db_file}"

    monkeypatch.setenv("SQLITE_URL", async_url)
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("API_SIGNING_SECRET", "test-secret")

    # Reset the container so get_container() picks up the patched env.
    from research_api.container import set_container

    set_container(None)

    ok, msg = _run_alembic_upgrade_head()
    assert ok, f"auto-migrate failed: {msg}"

    insp = inspect(create_engine(f"sqlite:///{db_file}"))
    tables = set(insp.get_table_names())
    # Should have alembic_version + the headline tables from the latest revs.
    assert "alembic_version" in tables
    assert "dataset_variables" in tables
    # 0022 adds dataset_variables.display_label
    cols = {c["name"] for c in insp.get_columns("dataset_variables")}
    assert "display_label" in cols, (
        "auto-migrate did not reach migration 0022; columns are: " + ", ".join(sorted(cols))
    )

    set_container(None)


@pytest.mark.asyncio
async def test_lifespan_startup_runs_auto_migrate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """End-to-end: app lifespan startup must leave a fresh DB at head.

    We explicitly UNSET ``DISABLE_AUTO_MIGRATE`` (set by conftest) so the
    lifespan actually invokes the migration step. The lifespan ctx is opened
    via ``app.router.lifespan_context`` so we drive the real startup sequence
    (httpx's ASGITransport does NOT dispatch lifespan events).
    """
    db_file = tmp_path / "startup.db"
    async_url = f"sqlite+aiosqlite:///{db_file}"

    monkeypatch.setenv("SQLITE_URL", async_url)
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("API_SIGNING_SECRET", "test-secret")
    monkeypatch.delenv("DISABLE_AUTO_MIGRATE", raising=False)

    from research_api.container import build_container, set_container
    from research_api.main import app
    from research_api.services.storage import LocalFsStorage

    container = build_container(
        storage=LocalFsStorage(root=tmp_path, signing_secret="test-secret"),
    )
    set_container(container)

    try:
        # Drive the lifespan context end-to-end. Entering the async context
        # runs the startup phase (including our auto-migrate step); exiting
        # runs the shutdown phase.
        async with app.router.lifespan_context(app):
            pass

        # After startup, the DB must be at head with the 0022 column present.
        assert db_file.exists(), (
            f"DB file {db_file} missing — auto-migrate did not run"
        )
        sync_url = f"sqlite:///{db_file}"
        insp = inspect(create_engine(sync_url))
        tables = set(insp.get_table_names())
        assert "alembic_version" in tables
        assert "dataset_variables" in tables
        cols = {c["name"] for c in insp.get_columns("dataset_variables")}
        assert "display_label" in cols
    finally:
        await container.engine.dispose()
        set_container(None)
        # Restore the test-suite default so subsequent tests aren't affected.
        os.environ["DISABLE_AUTO_MIGRATE"] = "1"


@pytest.mark.asyncio
async def test_500_response_carries_cors_headers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unhandled exceptions return a 500 JSON response WITH CORS headers.

    Pre-fix the browser saw a CORS error because Starlette's default 500
    bypassed CORSMiddleware. With our explicit handler attached the
    Access-Control-Allow-Origin header is stamped on every error response.
    """
    monkeypatch.setenv("SQLITE_URL", f"sqlite+aiosqlite:///{tmp_path}/x.db")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("API_SIGNING_SECRET", "test-secret")

    from research_api.container import build_container, set_container
    from research_api.db.base import Base
    from research_api.main import app
    from research_api.services.storage import LocalFsStorage

    container = build_container(
        storage=LocalFsStorage(root=tmp_path, signing_secret="test-secret"),
    )
    async with container.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    set_container(container)

    # Register a throwaway route that raises an unhandled exception. Doing
    # this inside the test (rather than in main.py) keeps the production
    # surface unchanged.
    @app.get("/__test_boom")
    async def _boom() -> dict:
        raise RuntimeError("kaboom")

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test",
        ) as client:
            resp = await client.get(
                "/__test_boom",
                headers={"Origin": "http://127.0.0.1:5173"},
            )
            assert resp.status_code == 500
            # The CORS headers MUST be present so the browser surfaces the
            # real error instead of mis-reporting it as a CORS failure.
            assert (
                resp.headers.get("access-control-allow-origin")
                == "http://127.0.0.1:5173"
            )
    finally:
        # Pop the test route so other tests aren't affected.
        app.router.routes = [r for r in app.router.routes if getattr(r, "path", None) != "/__test_boom"]
        await container.engine.dispose()
        set_container(None)
