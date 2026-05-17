"""Extract textual content from PDF or DOCX bytes.

Returns "" on any failure — the upstream pipeline degrades gracefully (falls back to
CrossRef DOI lookup or user manual entry). Never raises on malformed input.

Detection strategy: sniff magic bytes directly (libmagic is unreliable for DOCX,
which is a ZIP archive — reports application/octet-stream on some versions).
"""
from __future__ import annotations

import io
import zipfile

import magic
from docx import Document as DocxDocument
from pypdf import PdfReader

PDF_MIME = "application/pdf"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def detect_mime(data: bytes) -> str:
    """Best-effort MIME detection. Prefers explicit signatures for PDF and DOCX,
    falls back to libmagic for everything else."""
    if data.startswith(b"%PDF-"):
        return PDF_MIME
    # DOCX is a ZIP archive with a [Content_Types].xml that mentions wordprocessingml
    if data.startswith(b"PK\x03\x04") and _is_docx_zip(data):
        return DOCX_MIME
    return magic.from_buffer(data[:4096], mime=True)


# Zip-bomb guard: cap total uncompressed size across all members. A clean .docx
# rarely exceeds 20 MB uncompressed; 200 MB is generous and still safe.
_MAX_UNCOMPRESSED_BYTES = 200 * 1024 * 1024


def _safe_zip_total_size_ok(data: bytes) -> bool:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            total = sum(info.file_size for info in z.infolist())
            return total <= _MAX_UNCOMPRESSED_BYTES
    except (zipfile.BadZipFile, OSError):
        return False


def _is_docx_zip(data: bytes) -> bool:
    if not _safe_zip_total_size_ok(data):
        return False
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            try:
                ct = z.read("[Content_Types].xml").decode("utf-8", errors="ignore")
                return "wordprocessingml" in ct
            except KeyError:
                return False
    except (zipfile.BadZipFile, OSError):
        return False


def extract_first_pages_text(data: bytes, n: int = 2) -> str:
    if not data:
        return ""
    mime = detect_mime(data)
    if mime == PDF_MIME:
        return _from_pdf(data, n)
    if mime == DOCX_MIME:
        return _from_docx(data)
    return ""


def _from_pdf(data: bytes, n: int) -> str:
    try:
        reader = PdfReader(io.BytesIO(data))
        parts: list[str] = []
        for page in reader.pages[: max(1, n)]:
            try:
                parts.append(page.extract_text() or "")
            except Exception:
                continue
        return "\n".join(parts).strip()
    except Exception:
        return ""


def _from_docx(data: bytes) -> str:
    # Same zip-bomb guard before python-docx parses
    if not _safe_zip_total_size_ok(data):
        return ""
    try:
        doc = DocxDocument(io.BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs if p.text).strip()
    except Exception:
        return ""
