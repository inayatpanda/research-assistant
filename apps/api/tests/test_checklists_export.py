"""Phase 20 (MP20) — Completed checklist PDF + DOCX export.

We assert byte-level magic numbers (PDF = ``%PDF``, DOCX = ``PK``) and
the presence of a couple of cell strings inside the DOCX so the table is
actually written.
"""
from __future__ import annotations

import io
import zipfile

from research_api.services.checklists.export import render_docx, render_pdf


_ITEMS = [
    {
        "item_id": "1",
        "item_text": "Title and abstract",
        "status": "pass",
        "comment": "Looks good",
        "mapped_section": "Title",
        "mapped_text_excerpt": "A randomised trial of …",
    },
    {
        "item_id": "2",
        "item_text": "Background and objectives",
        "status": "fail",
        "comment": "Add hypothesis",
        "mapped_section": None,
        "mapped_text_excerpt": None,
    },
    {
        "item_id": "3",
        "item_text": "Trial design",
        "status": "unclear",
        "comment": "",
        "mapped_section": "Methods",
        "mapped_text_excerpt": "Parallel-group design …",
    },
    {
        "item_id": "4",
        "item_text": "Eligibility criteria",
        "status": "na",
        "comment": "",
        "mapped_section": None,
        "mapped_text_excerpt": None,
    },
]


def test_render_pdf_returns_valid_pdf_bytes() -> None:
    blob = render_pdf(
        checklist_name="CONSORT 2010",
        run_title="v1 to JBJS",
        items=_ITEMS,
        compliance_pct=33.3,
    )
    assert blob.startswith(b"%PDF"), "render_pdf must emit a PDF byte stream"
    # A non-trivial 4-row table + header + summary should be at least a
    # couple of KB.
    assert len(blob) > 800


def test_render_docx_returns_valid_zip_with_document_xml() -> None:
    blob = render_docx(
        checklist_name="CONSORT 2010",
        run_title="v1 to JBJS",
        items=_ITEMS,
        compliance_pct=33.3,
    )
    # DOCX is a ZIP archive — should start with ``PK``.
    assert blob[:2] == b"PK", "render_docx must emit a ZIP / DOCX byte stream"

    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        names = set(zf.namelist())
        assert "word/document.xml" in names
        body = zf.read("word/document.xml").decode("utf-8", errors="replace")

    # Cells should mention our item ids + statuses (in case-correct form).
    assert "CONSORT 2010" in body
    assert "v1 to JBJS" in body
    assert "Pass" in body and "Fail" in body and "Unclear" in body and "N/A" in body


def test_render_pdf_handles_empty_items_gracefully() -> None:
    """Edge case: an empty checklist should still render a valid PDF (header only)."""
    blob = render_pdf(
        checklist_name="Empty",
        run_title="(none)",
        items=[],
        compliance_pct=0.0,
    )
    assert blob.startswith(b"%PDF")
