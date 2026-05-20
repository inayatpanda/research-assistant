import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .container import get_container

logger = logging.getLogger(__name__)


def _run_alembic_upgrade_head() -> tuple[bool, str]:
    """Programmatically run ``alembic upgrade head`` against the configured DB.

    Returns (ok, message). On failure we log loudly but never re-raise; the
    caller decides whether to keep booting so the user gets a clear API error
    rather than a refused connection.
    """
    try:
        from alembic import command
        from alembic.config import Config
    except Exception as exc:  # pragma: no cover - alembic always installed
        return False, f"alembic import failed: {exc!r}"

    # alembic.ini lives at apps/api/alembic.ini — two parents up from this file
    # (apps/api/src/research_api/main.py).
    ini_path = Path(__file__).resolve().parents[2] / "alembic.ini"
    if not ini_path.exists():
        return False, f"alembic.ini not found at {ini_path}"

    settings = get_container().settings
    # The sync alembic URL must NOT contain the +aiosqlite driver. Strip it so
    # ``alembic upgrade`` uses the plain sqlite driver.
    async_url = settings.sqlite_url
    sync_url = async_url.replace("+aiosqlite", "", 1)

    # Build the Config WITHOUT passing alembic.ini, so alembic doesn't invoke
    # ``fileConfig`` against it — which would globally reconfigure logging and
    # break unrelated tests that rely on the default propagation behaviour.
    cfg = Config()
    cfg.set_main_option("script_location", str(ini_path.parent / "alembic"))
    cfg.set_main_option("sqlalchemy.url", sync_url)
    # Belt-and-braces: env.py honours ALEMBIC_SQLALCHEMY_URL if set, which
    # guarantees our caller-supplied URL wins even if env.py is reloaded.
    prev_url = os.environ.get("ALEMBIC_SQLALCHEMY_URL")
    os.environ["ALEMBIC_SQLALCHEMY_URL"] = sync_url
    try:
        command.upgrade(cfg, "head")
        return True, f"alembic upgraded to head ({sync_url})"
    except Exception as exc:
        return False, f"alembic upgrade failed: {exc!r}"
    finally:
        if prev_url is None:
            os.environ.pop("ALEMBIC_SQLALCHEMY_URL", None)
        else:
            os.environ["ALEMBIC_SQLALCHEMY_URL"] = prev_url
from .routes.abbreviations import router as abbreviations_router
from .routes.analyses import router as analyses_router
from .routes.analysis_plans import router as analysis_plans_router
from .routes.articles import router as articles_router
from .routes.comments import router as comments_router
from .routes.compilation import router as compilation_router
from .routes.cover_letter import router as cover_letter_router
from .routes.datasets import router as datasets_router
from .routes.consort import router as consort_router
from .routes.diagnostics import router as diagnostics_router
from .routes.economic_analyses import router as economic_analyses_router
from .routes.export import router as export_router
from .routes.figures import router as figures_router
from .routes.files import router as files_router
from .routes.frontmatter import router as frontmatter_router
from .routes.grade import router as grade_router
from .routes.health import router as health_router
from .routes.highlights import router as highlights_router
from .routes.ingest import router as ingest_router
from .routes.journal_templates import router as journal_templates_router
from .routes.living import router as living_router
from .routes.manuscript_sections import router as manuscript_sections_router
from .routes.notes import router as notes_router
from .routes.plots import router as plots_router
from .routes.power import router as power_router
from .routes.projects import router as projects_router
from .routes.prospero import router as prospero_router
from .routes.psm import router as psm_router
from .routes.reviewer_response import router as reviewer_response_router
from .routes.mesh import router as mesh_router
from .routes.meta_extensions import router as meta_extensions_router
from .routes.reviews import router as reviews_router
from .routes.reviews_meta import router as reviews_meta_router
from .routes.search_strategies import router as search_strategies_router
from .routes.sr_depth import router as sr_depth_router
from .routes.snapshots import router as snapshots_router
from .routes.stats_depth import router as stats_depth_router
from .routes.transformations import router as transformations_router
from .routes.cross_dataset import router as cross_dataset_router
from .routes.writing import router as writing_router

@asynccontextmanager
async def _lifespan(_app: FastAPI):
    # DEMO-FIX-D HIGH-1 — auto-apply alembic migrations on every boot so the
    # live DB schema cannot drift behind the ORM models. Runs BEFORE the
    # scheduler init (the scheduler reads tables added by 0019). Failures are
    # logged loudly but do NOT crash boot so the user gets a clear API error
    # instead of a refused connection.
    if os.environ.get("DISABLE_AUTO_MIGRATE") != "1":
        ok, msg = _run_alembic_upgrade_head()
        if ok:
            logger.info("auto-migrate: %s", msg)
        else:
            logger.error("auto-migrate FAILED: %s", msg)

    # Lazy import — keeps app import cheap and avoids touching the scheduler
    # module during static analysis of the bare module.
    from .services.scheduler.runner import init_scheduler, shutdown_scheduler

    await init_scheduler(_app)
    try:
        yield
    finally:
        await shutdown_scheduler(_app)


app = FastAPI(
    title="Research Manuscript Assistant API",
    version="0.0.1",
    lifespan=_lifespan,
)

_settings = get_container().settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
)


# DEMO-FIX-D HIGH-1 — Ensure unhandled exceptions return a JSONResponse with
# CORS headers attached so the browser surfaces a real 500 instead of mis-
# reporting it as a CORS error. Starlette's default ServerErrorMiddleware
# bypasses CORSMiddleware for unhandled exceptions; this handler runs INSIDE
# the middleware stack so CORS headers get stamped on the response.
def _cors_headers_for(request: Request) -> dict[str, str]:
    origin = request.headers.get("origin")
    if not origin:
        return {}
    if origin in _settings.cors_origins:
        return {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Vary": "Origin",
        }
    return {}


@app.exception_handler(Exception)
async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
        headers=_cors_headers_for(request),
    )


@app.exception_handler(StarletteHTTPException)
async def _http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers={**(exc.headers or {}), **_cors_headers_for(request)},
    )

app.include_router(health_router)
app.include_router(files_router)
app.include_router(projects_router, prefix="/api")
app.include_router(articles_router, prefix="/api")
app.include_router(ingest_router, prefix="/api")
app.include_router(highlights_router, prefix="/api")
app.include_router(notes_router, prefix="/api")
app.include_router(compilation_router, prefix="/api")
app.include_router(manuscript_sections_router, prefix="/api")
app.include_router(abbreviations_router, prefix="/api")
app.include_router(writing_router, prefix="/api")
app.include_router(datasets_router, prefix="/api")
app.include_router(analyses_router, prefix="/api")
app.include_router(reviews_router, prefix="/api")
app.include_router(reviews_meta_router, prefix="/api")
app.include_router(export_router, prefix="/api")
app.include_router(figures_router, prefix="/api")
app.include_router(consort_router, prefix="/api")
app.include_router(journal_templates_router, prefix="/api")
app.include_router(frontmatter_router, prefix="/api")
app.include_router(snapshots_router, prefix="/api")
app.include_router(comments_router, prefix="/api")
app.include_router(cover_letter_router, prefix="/api")
app.include_router(reviewer_response_router, prefix="/api")
app.include_router(power_router, prefix="/api")
app.include_router(psm_router, prefix="/api")
app.include_router(transformations_router, prefix="/api")
app.include_router(cross_dataset_router, prefix="/api")
app.include_router(plots_router, prefix="/api")
app.include_router(analysis_plans_router, prefix="/api")
app.include_router(grade_router, prefix="/api")
app.include_router(prospero_router, prefix="/api")
app.include_router(living_router, prefix="/api")
app.include_router(mesh_router, prefix="/api")
app.include_router(search_strategies_router, prefix="/api")
app.include_router(sr_depth_router, prefix="/api")
app.include_router(meta_extensions_router, prefix="/api")
# Phase 17 (MP17) — Stats depth: populations / imputation / CACE / sensitivity
# / IRR / instruments / post-hoc / instrument-binding.
app.include_router(stats_depth_router, prefix="/api")
# DEMO-FIX-A — Standalone diagnostic-tests panel (Shapiro / Levene / KS / etc.)
app.include_router(diagnostics_router, prefix="/api")
# Phase 18 (MP18) — Health Economics module (QALYs / ICER / CEAC / CHEERS).
app.include_router(economic_analyses_router, prefix="/api")
