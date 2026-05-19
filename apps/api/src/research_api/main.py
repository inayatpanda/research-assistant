from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .container import get_container
from .routes.abbreviations import router as abbreviations_router
from .routes.analyses import router as analyses_router
from .routes.analysis_plans import router as analysis_plans_router
from .routes.articles import router as articles_router
from .routes.comments import router as comments_router
from .routes.compilation import router as compilation_router
from .routes.cover_letter import router as cover_letter_router
from .routes.datasets import router as datasets_router
from .routes.consort import router as consort_router
from .routes.export import router as export_router
from .routes.figures import router as figures_router
from .routes.files import router as files_router
from .routes.frontmatter import router as frontmatter_router
from .routes.grade import router as grade_router
from .routes.health import router as health_router
from .routes.highlights import router as highlights_router
from .routes.ingest import router as ingest_router
from .routes.journal_templates import router as journal_templates_router
from .routes.manuscript_sections import router as manuscript_sections_router
from .routes.notes import router as notes_router
from .routes.plots import router as plots_router
from .routes.power import router as power_router
from .routes.projects import router as projects_router
from .routes.prospero import router as prospero_router
from .routes.psm import router as psm_router
from .routes.reviewer_response import router as reviewer_response_router
from .routes.reviews import router as reviews_router
from .routes.reviews_meta import router as reviews_meta_router
from .routes.snapshots import router as snapshots_router
from .routes.transformations import router as transformations_router
from .routes.cross_dataset import router as cross_dataset_router
from .routes.writing import router as writing_router

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
