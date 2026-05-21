"""Phase E1 — Frozen-mode entry point.

This module lets the FastAPI app run as a self-contained executable when
PyInstaller freezes the backend. The Electron shell spawns the produced
binary with ``RMA_HOST`` / ``RMA_PORT`` (and optionally other env vars) and
this entry calls uvicorn programmatically.

We deliberately keep the surface tiny: no CLI flag parsing, no
plugin-loading. Environment variables drive every knob so the Electron main
process can stay platform-agnostic.

* ``RMA_HOST``  — interface to bind (default ``127.0.0.1``).
* ``RMA_PORT``  — TCP port (default ``8787``).
* ``RMA_LOG_LEVEL`` — uvicorn log level (default ``info``).
* ``RMA_RELOAD`` — set to ``1`` to enable hot reload (dev only, never in
  the packaged build).

Running ``python -m research_api`` in source mode also goes through this
entry point so the dev-mode invocation matches the frozen binary exactly.
"""
from __future__ import annotations

import argparse
import os
import sys


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="research_api",
        description=(
            "Research Manuscript Assistant backend. Spawned by the Electron "
            "shell in production; runnable directly for smoke tests."
        ),
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("RMA_HOST", "127.0.0.1"),
        help="Bind address (env: RMA_HOST). Defaults to 127.0.0.1.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("RMA_PORT", "8787")),
        help="TCP port (env: RMA_PORT). Defaults to 8787.",
    )
    parser.add_argument(
        "--log-level",
        default=os.environ.get("RMA_LOG_LEVEL", "info"),
        help="uvicorn log level (env: RMA_LOG_LEVEL).",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=_bool_env("RMA_RELOAD"),
        help="Enable uvicorn reload (dev only).",
    )
    args = parser.parse_args(argv)

    # Lazy import — keeps ``--help`` cheap and lets PyInstaller analyse the
    # dependency graph through the explicit import statement.
    import uvicorn

    from research_api.main import app  # noqa: F401  ensure side-effects run

    uvicorn.run(
        "research_api.main:app",
        host=args.host,
        port=args.port,
        log_level=args.log_level,
        reload=args.reload,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry
    sys.exit(main())
