"""Phase 4.6 — AI peer-review services.

* ``manuscript_extractor`` — flattens in-app manuscript sections into a
  single peer-reviewable text block plus structural metadata.
* ``file_extractor`` — extracts text from uploaded PDF/DOCX bytes.
* ``export`` — renders the structured critique to DOCX/PDF.
"""
from .manuscript_extractor import (
    ManuscriptExtraction,
    extract_manuscript_for_peer_review,
)
from .file_extractor import (
    FileExtraction,
    PeerReviewExtractError,
    extract_uploaded_document,
)
from .export import render_critique_docx, render_critique_pdf

__all__ = [
    "ManuscriptExtraction",
    "extract_manuscript_for_peer_review",
    "FileExtraction",
    "PeerReviewExtractError",
    "extract_uploaded_document",
    "render_critique_docx",
    "render_critique_pdf",
]
