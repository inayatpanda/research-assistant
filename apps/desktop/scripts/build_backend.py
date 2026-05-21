#!/usr/bin/env python3
"""Phase E1 — Wrapper around PyInstaller that freezes the FastAPI backend.

Usage::

    cd apps/desktop
    python scripts/build_backend.py [--clean]

Outputs:
    dist/backend/research_api/research_api[.exe]
    dist/backend/research_api/_internal/...

The script auto-discovers the project's venv Python (``apps/api/.venv``)
and falls back to ``sys.executable`` if the venv is missing. PyInstaller
must be installed in whichever interpreter is used.

We invoke PyInstaller via ``python -m PyInstaller`` rather than the
``pyinstaller`` console script so the right interpreter — and therefore
the right site-packages — is guaranteed.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

DESKTOP_DIR = Path(__file__).resolve().parent.parent
SPEC_PATH = DESKTOP_DIR / "research_api.spec"
DIST_PATH = DESKTOP_DIR / "dist" / "backend"
WORK_PATH = DESKTOP_DIR / "build" / "backend"


def _find_python() -> str:
    """Prefer the apps/api venv so PyInstaller sees scipy/etc."""
    repo_root = DESKTOP_DIR.parent.parent
    venv_bin = repo_root / "apps" / "api" / ".venv" / "bin" / "python"
    if venv_bin.exists():
        return str(venv_bin)
    venv_win = repo_root / "apps" / "api" / ".venv" / "Scripts" / "python.exe"
    if venv_win.exists():
        return str(venv_win)
    return sys.executable


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Wipe dist/ and build/ before building (slower, more reliable).",
    )
    args = parser.parse_args(argv)

    if not SPEC_PATH.exists():
        print(f"error: spec not found at {SPEC_PATH}", file=sys.stderr)
        return 1

    if args.clean:
        for d in (DIST_PATH, WORK_PATH):
            if d.exists():
                print(f"removing {d}")
                shutil.rmtree(d)

    DIST_PATH.mkdir(parents=True, exist_ok=True)
    WORK_PATH.mkdir(parents=True, exist_ok=True)

    python = _find_python()
    cmd = [
        python,
        "-m",
        "PyInstaller",
        str(SPEC_PATH),
        "--distpath",
        str(DIST_PATH),
        "--workpath",
        str(WORK_PATH),
        "--noconfirm",
    ]
    print("running:", " ".join(cmd))
    env = os.environ.copy()
    # Make sure PyInstaller imports the project as a package — the spec
    # already lists pathex, but a belt-and-braces PYTHONPATH never hurts.
    env.setdefault(
        "PYTHONPATH",
        str(DESKTOP_DIR.parent / "api" / "src"),
    )
    return subprocess.call(cmd, env=env)


if __name__ == "__main__":
    raise SystemExit(main())
