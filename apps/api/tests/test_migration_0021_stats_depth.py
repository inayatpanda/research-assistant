"""Regression: migration 0021 must apply cleanly against a fresh SQLite DB.

E2E-sweep bug #S1 — the original revision used anonymous
`sa.ForeignKey(...)` inside `op.batch_alter_table("analyses") as batch:`,
which crashes under SQLite batch-mode because the rebuild step refuses
unnamed constraints.

This test invokes `alembic upgrade head` as a subprocess (overriding the
DB URL via the `-x` switch so env.py points at a tmp DB) and asserts the
upgrade succeeds + the named FK is present.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect


API_ROOT = Path(__file__).resolve().parents[1]
ALEMBIC_BIN = API_ROOT / ".venv" / "bin" / "alembic"


@pytest.mark.skipif(not ALEMBIC_BIN.exists(), reason="alembic venv not present")
def test_upgrade_head_against_fresh_db(tmp_path: Path) -> None:
    """`alembic upgrade head` must succeed against an empty DB.

    We use a wrapper script that overrides the alembic env's DB path via
    an environment variable. The env.py hardcodes the path, so we patch
    it on the fly using a small monkeypatch script.
    """
    db_file = tmp_path / "fresh.db"

    # Run a small Python script that monkey-patches env.py path resolution
    # then invokes alembic upgrade head.
    runner = f"""
import sys, os
from pathlib import Path
target_db = Path({str(db_file)!r})

# Patch env.py's data path resolution by intercepting the
# `_data_dir / 'research.db'` URL string.
import research_api.db.base as _b  # noqa
from alembic.config import Config
from alembic import command

cfg = Config({str(API_ROOT / 'alembic.ini')!r})
cfg.set_main_option('script_location', {str(API_ROOT / 'alembic')!r})
cfg.set_main_option('sqlalchemy.url', f'sqlite:///{{target_db}}')

# env.py overrides sqlalchemy.url after Config loads; monkeypatch the
# alembic.env module to skip that override.
import alembic.context as _ctx
orig_set_main_option = cfg.set_main_option
def keep_override(name, val):
    if name == 'sqlalchemy.url' and 'research.db' in val and 'fresh.db' not in val:
        return
    orig_set_main_option(name, val)
cfg.set_main_option = keep_override

command.upgrade(cfg, 'head')
"""
    proc = subprocess.run(
        [sys.executable, "-c", runner],
        cwd=str(API_ROOT),
        env={**os.environ, "PYTHONPATH": str(API_ROOT / "src")},
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, (
        f"alembic upgrade head failed:\n"
        f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
    )

    insp = inspect(create_engine(f"sqlite:///{db_file}"))
    tables = set(insp.get_table_names())
    assert "analysis_populations" in tables
    assert "imputation_runs" in tables

    fks = insp.get_foreign_keys("analyses")
    population_fks = [
        fk for fk in fks if "population_id" in (fk.get("constrained_columns") or [])
    ]
    assert population_fks, "analyses.population_id FK is missing"
    assert population_fks[0]["name"] == "fk_analyses_population_id", (
        "FK must be explicitly named for SQLite batch-mode compatibility"
    )
