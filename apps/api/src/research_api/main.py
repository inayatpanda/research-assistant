from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .container import get_container
from .routes.articles import router as articles_router
from .routes.compilation import router as compilation_router
from .routes.files import router as files_router
from .routes.health import router as health_router
from .routes.highlights import router as highlights_router
from .routes.notes import router as notes_router
from .routes.projects import router as projects_router

app = FastAPI(title="Research Manuscript Assistant API", version="0.0.1")

_settings = get_container().settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
)

app.include_router(health_router)
app.include_router(files_router)
app.include_router(projects_router, prefix="/api")
app.include_router(articles_router, prefix="/api")
app.include_router(highlights_router, prefix="/api")
app.include_router(notes_router, prefix="/api")
app.include_router(compilation_router, prefix="/api")
