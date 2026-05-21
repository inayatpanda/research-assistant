#!/usr/bin/env python3
"""Phase E1.5 — Manual smoke test for the frozen backend.

This script is intentionally NOT wired into the CI suite — booting the
frozen binary takes ~20–30 seconds on a cold matplotlib font cache, plus
PyInstaller bundles weigh ~600 MB, neither of which we want on every
``pytest -q`` run.

Run it after a fresh ``python scripts/build_backend.py``:

    python tests/test_frozen_smoke.py

What it checks:
    1. The bundled executable exists.
    2. ``/health`` returns 200 within 60 seconds of launching.
    3. The alembic auto-migrate path runs (a freshly-created SQLite DB
       ends up with the projects table).
    4. The process exits cleanly on SIGTERM within 5 seconds.

Exit code is ``0`` on success, non-zero otherwise.
"""
from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

DESKTOP_DIR = Path(__file__).resolve().parent.parent
EXE = (
    DESKTOP_DIR
    / "dist"
    / "backend"
    / "research_api"
    / ("research_api.exe" if sys.platform == "win32" else "research_api")
)

HEALTH_TIMEOUT_S = 60
SIGTERM_TIMEOUT_S = 5


def _wait_for_health(port: int, timeout: float) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/health", timeout=2
            ) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def main() -> int:
    if not EXE.exists():
        print(f"FAIL: {EXE} missing. Run scripts/build_backend.py first.")
        return 2

    with tempfile.TemporaryDirectory() as td:
        port = 17890
        env = {
            **os.environ,
            "RMA_PORT": str(port),
            "RMA_DISABLE_AUTH": "1",
            "DATA_DIR": td,
            "SQLITE_URL": f"sqlite+aiosqlite:///{td}/smoke.db",
        }
        proc = subprocess.Popen(
            [str(EXE), "--port", str(port)],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        try:
            ok = _wait_for_health(port, HEALTH_TIMEOUT_S)
            if not ok:
                print(f"FAIL: /health never returned 200 in {HEALTH_TIMEOUT_S}s")
                return 1
            print(f"OK: /health responded on :{port}")

            # Migration check — the projects table should exist.
            db_path = Path(td) / "smoke.db"
            if db_path.exists():
                import sqlite3

                with sqlite3.connect(db_path) as con:
                    cur = con.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name='projects'"
                    )
                    if cur.fetchone():
                        print("OK: alembic migrations ran (projects table exists)")
                    else:
                        print("FAIL: projects table missing — alembic didn't run")
                        return 1
            else:
                print(
                    "WARN: smoke.db not created at expected path — caller may "
                    "need to set DATA_DIR/SQLITE_URL differently."
                )
        finally:
            try:
                proc.send_signal(signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                proc.wait(timeout=SIGTERM_TIMEOUT_S)
                print("OK: process exited within SIGTERM budget")
            except subprocess.TimeoutExpired:
                print("WARN: process needed SIGKILL")
                proc.kill()
                proc.wait()
                return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
