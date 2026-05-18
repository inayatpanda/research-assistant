"""Phase 8.7 — Figure magic-byte validation."""
from __future__ import annotations

from pathlib import Path

import pytest

from research_api.services.figures.validation import (
    FIGURE_SIZE_CAP_MB,
    FigureValidationError,
    validate_image_bytes,
)

FIX = Path(__file__).parent / "fixtures"


def test_validate_png_returns_dimensions() -> None:
    data = (FIX / "tiny.png").read_bytes()
    vi = validate_image_bytes(data)
    assert vi.mime == "image/png"
    assert vi.width_px == 4
    assert vi.height_px == 4
    assert vi.byte_size == len(data)


def test_validate_jpeg_returns_dimensions() -> None:
    data = (FIX / "tiny.jpg").read_bytes()
    vi = validate_image_bytes(data)
    assert vi.mime == "image/jpeg"
    assert vi.width_px == 4
    assert vi.height_px == 4


def test_validate_svg_accepts_with_no_dimensions() -> None:
    data = (FIX / "tiny.svg").read_bytes()
    vi = validate_image_bytes(data)
    assert vi.mime == "image/svg+xml"
    assert vi.width_px is None
    assert vi.height_px is None


def test_validate_pdf_disguised_as_png_rejects() -> None:
    data = (FIX / "totally_not_a_png.bin").read_bytes()
    with pytest.raises(FigureValidationError):
        validate_image_bytes(data)


def test_validate_empty_bytes_rejects() -> None:
    with pytest.raises(FigureValidationError):
        validate_image_bytes(b"")


def test_validate_oversize_bytes_rejects() -> None:
    cap_bytes = FIGURE_SIZE_CAP_MB * 1024 * 1024
    oversized = b"\x89PNG\r\n\x1a\n" + (b"\x00" * (cap_bytes))
    with pytest.raises(FigureValidationError):
        validate_image_bytes(oversized)


def test_validate_truncated_png_rejects() -> None:
    # Valid PNG signature but no IHDR / body — Pillow should fail
    only_signature = b"\x89PNG\r\n\x1a\nGARBAGE"
    with pytest.raises(FigureValidationError):
        validate_image_bytes(only_signature)


def test_validate_svg_without_open_tag_rejects() -> None:
    # Looks vaguely XML but no <svg
    text = b"<?xml version='1.0'?><html><body>hi</body></html>"
    with pytest.raises(FigureValidationError):
        validate_image_bytes(text)


def test_validate_svg_with_xml_prelude_accepts() -> None:
    text = b"<?xml version='1.0'?>\n<svg xmlns='http://www.w3.org/2000/svg'/>"
    vi = validate_image_bytes(text)
    assert vi.mime == "image/svg+xml"
