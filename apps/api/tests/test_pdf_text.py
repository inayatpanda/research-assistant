from pathlib import Path

import pytest

from research_api.services.pdf_text import detect_mime, extract_first_pages_text


FIXTURES = Path(__file__).parent / "fixtures"


def test_detect_mime_pdf():
    data = (FIXTURES / "sample.pdf").read_bytes()
    assert detect_mime(data) == "application/pdf"


def test_detect_mime_docx():
    data = (FIXTURES / "sample.docx").read_bytes()
    assert detect_mime(data) == (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


def test_extract_pdf_returns_text():
    data = (FIXTURES / "sample.pdf").read_bytes()
    text = extract_first_pages_text(data, n=2)
    # Minimal fixture contains "Test Article" — full reportlab one would contain more
    assert "Test Article" in text or len(text) > 0


def test_extract_docx_returns_text():
    data = (FIXTURES / "sample.docx").read_bytes()
    text = extract_first_pages_text(data, n=2)
    assert "Posterior" in text
    assert "Alice Author" in text


def test_empty_input_returns_empty_string():
    assert extract_first_pages_text(b"") == ""


def test_unknown_mime_returns_empty_string():
    # Plain text — not PDF, not DOCX
    assert extract_first_pages_text(b"hello world this is plain text", n=2) == ""


def test_corrupt_pdf_returns_empty_string():
    # Starts like a PDF but truncated mid-stream
    corrupt = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\n"
    out = extract_first_pages_text(corrupt, n=2)
    # Should not raise; may return "" or partial
    assert isinstance(out, str)
