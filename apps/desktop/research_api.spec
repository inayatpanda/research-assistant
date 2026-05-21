# -*- mode: python ; coding: utf-8 -*-
"""Phase E1 — PyInstaller spec for the Research Assistant backend.

Produces a one-folder bundle (``onedir``) under
``apps/desktop/dist/backend/research_api/`` containing the frozen FastAPI
executable + all Python deps + the alembic migrations + the Learn hub
markdown content. The Electron shell spawns this executable as a
subprocess at launch.

Build via the wrapper script::

    cd apps/desktop
    python scripts/build_backend.py

The spec file resolves repo paths relative to its own location
(``apps/desktop/research_api.spec``) so it works from any CWD.

PyInstaller gotchas we hit during E1:

* SciPy ships C-extension submodules that don't expose themselves through
  static analysis. We force-import ``scipy.special.cython_special`` and
  ``scipy.stats`` so the cython binaries land in the bundle.
* statsmodels has lazy ``__getattr__`` magic for its sub-packages; we
  blanket-add ``statsmodels.tsa`` + ``statsmodels.api`` to be safe.
* matplotlib's backend loader picks one at import time; we exclude Tk/Qt
  backends and only bundle ``backend_agg`` (we render PNGs server-side).
* alembic resolves its env.py via a script-location path, so the
  ``alembic/`` tree has to be present on disk as data — not pyz'd.
* Learn hub markdown lives under ``research_api/learn/<category>/*.md``
  and is read via ``Path(__file__).parent`` at runtime — keep the on-disk
  layout intact.

Code signing is intentionally skipped (free-tier constraint); the user
right-clicks → Open on macOS and clicks "Run anyway" on Windows.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Spec files are exec'd by PyInstaller with ``__file__`` set to the spec
# path, but only on >= 6.x. Fall back to CWD for older runs.
SPEC_PATH = Path(globals().get("__file__", os.path.abspath(sys.argv[0]))).resolve()
DESKTOP_DIR = SPEC_PATH.parent
REPO_ROOT = DESKTOP_DIR.parent.parent
API_ROOT = REPO_ROOT / "apps" / "api"
API_SRC = API_ROOT / "src"

# Entry — the __main__ inside the research_api package runs uvicorn.
entry_script = API_SRC / "research_api" / "__main__.py"

# Datas — pairs of (source-on-disk, target-relative-to-bundle).
# Onedir mode puts these into ``_internal/`` next to the launcher. Our
# main.py's ``_resolve_alembic_dir()`` helper looks for both
# ``_internal/alembic`` and ``sys._MEIPASS/alembic``, so either target
# layout works.
datas = [
    (str(API_ROOT / "alembic"), "alembic"),
    (str(API_ROOT / "alembic.ini"), "."),
    (
        str(API_SRC / "research_api" / "learn"),
        os.path.join("research_api", "learn"),
    ),
]

# Hidden imports — packages PyInstaller can't see via static analysis but
# which actually get imported at runtime (via importlib, __getattr__, or
# string lookup). Keep this list ordered roughly by the layer that needs
# the dep so future maintainers can prune confidently.
hiddenimports = [
    # --- FastAPI / Uvicorn stack ---
    "fastapi",
    "uvicorn",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    # --- DB / migrations ---
    "aiosqlite",
    "alembic",
    "alembic.runtime",
    "alembic.runtime.migration",
    "alembic.runtime.environment",
    "alembic.script",
    "alembic.ddl",
    "alembic.ddl.sqlite",
    "sqlalchemy",
    "sqlalchemy.dialects.sqlite",
    "sqlalchemy.dialects.sqlite.aiosqlite",
    "sqlalchemy.ext.asyncio",
    "pydantic",
    "pydantic_settings",
    # --- Scientific stack (PyInstaller misses cython binaries) ---
    "scipy",
    "scipy.special",
    "scipy.special.cython_special",
    "scipy.stats",
    "scipy.stats._stats",
    "scipy.linalg",
    "scipy.sparse",
    "numpy",
    "pandas",
    "pandas._libs",
    "pandas._libs.tslibs",
    "statsmodels",
    "statsmodels.api",
    "statsmodels.tsa",
    "statsmodels.tsa.api",
    "statsmodels.regression",
    "statsmodels.regression.linear_model",
    "statsmodels.regression.mixed_linear_model",
    "pingouin",
    "lifelines",
    # --- Plotting / exports ---
    "matplotlib",
    "matplotlib.backends.backend_agg",
    "reportlab",
    "reportlab.pdfgen",
    "reportlab.platypus",
    "PIL",
    "PIL._tkinter_finder",
    "svglib",
    "openpyxl",
    "docx",  # python-docx is imported as ``docx``
    # --- Ingestion / external APIs ---
    "httpx",
    "respx",
    "rapidfuzz",
    "bibtexparser",
    "tenacity",
    # --- Scheduler ---
    "apscheduler",
    "apscheduler.schedulers",
    "apscheduler.schedulers.asyncio",
    "apscheduler.jobstores",
    "apscheduler.jobstores.memory",
    "apscheduler.triggers",
    "apscheduler.triggers.interval",
    "apscheduler.triggers.cron",
    # --- AI providers (optional at runtime) ---
    "google.generativeai",
    "pypdf",
    "magic",  # python-magic is imported as ``magic``
    # --- yaml (Learn hub frontmatter parser) ---
    "yaml",
]

# Excludes — keep the bundle lean and skip GUI backends we never call.
excludes = [
    "matplotlib.backends.backend_tkagg",
    "matplotlib.backends.backend_qt5agg",
    "matplotlib.backends.backend_qt5",
    "matplotlib.backends.backend_qt6agg",
    "matplotlib.backends.backend_qt",
    "matplotlib.tests",
    "scipy.tests",
    "numpy.tests",
    "pandas.tests",
    "statsmodels.tests",
    "tkinter",
    "PyQt5",
    "PyQt6",
    "PySide2",
    "PySide6",
    "IPython",
    "jupyter",
    "notebook",
]


block_cipher = None


a = Analysis(
    [str(entry_script)],
    pathex=[str(API_SRC)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="research_api",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="research_api",
)
