"""Figure-upload validation: magic-byte sniff + Pillow dimension probe.

Allowed MIME types are PNG, JPEG, and SVG. PDFs, octet-stream blobs, and
truncated images are rejected. The 10 MiB cap matches the route-level guard.

SVG never reaches Pillow — Pillow has no native SVG support, and parsing
untrusted XML through an arbitrary library is a known XXE / XML-bomb risk.
For SVG we accept it as bytes after two cheap checks (XML prelude or `<svg`
literal in the first 1 KiB).
"""
from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Literal

from PIL import Image, UnidentifiedImageError


ALLOWED_FIGURE_MIME = frozenset({"image/png", "image/jpeg", "image/svg+xml"})
FIGURE_SIZE_CAP_MB = 10
_FIGURE_SIZE_CAP_BYTES = FIGURE_SIZE_CAP_MB * 1024 * 1024


class FigureValidationError(ValueError):
    """Raised for any rejection during validate_image_bytes."""


@dataclass(frozen=True)
class ValidatedImage:
    mime: Literal["image/png", "image/jpeg", "image/svg+xml"]
    width_px: int | None
    height_px: int | None
    byte_size: int


def _is_svg(data: bytes) -> bool:
    """Cheap sniff: first 1 KiB contains '<svg' (possibly after an XML prelude)."""
    head = data[:1024].lstrip()
    if head.startswith(b"<?xml"):
        # find the '<svg' tag in the remainder of the first 1 KiB
        return b"<svg" in data[:1024]
    return head.startswith(b"<svg")


def validate_image_bytes(data: bytes) -> ValidatedImage:
    """Sniff the magic bytes; return a ValidatedImage or raise.

    PNG: starts with the 8-byte signature `\\x89PNG\\r\\n\\x1a\\n`.
    JPEG: starts with `\\xff\\xd8\\xff`.
    SVG: contains `<svg` in its first 1 KiB (after optional XML prelude).
    """
    if not data:
        raise FigureValidationError("empty file")
    if len(data) > _FIGURE_SIZE_CAP_BYTES:
        raise FigureValidationError(
            f"file exceeds {FIGURE_SIZE_CAP_MB} MiB cap"
        )

    # PNG
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        try:
            with Image.open(io.BytesIO(data)) as im:
                im.verify()  # verify catches corrupted PNG bodies
            with Image.open(io.BytesIO(data)) as im:
                w, h = im.size
        except (UnidentifiedImageError, OSError, ValueError) as e:
            raise FigureValidationError(f"corrupt PNG: {e}") from e
        return ValidatedImage(
            mime="image/png", width_px=int(w), height_px=int(h), byte_size=len(data)
        )

    # JPEG
    if data.startswith(b"\xff\xd8\xff"):
        try:
            with Image.open(io.BytesIO(data)) as im:
                im.verify()
            with Image.open(io.BytesIO(data)) as im:
                w, h = im.size
        except (UnidentifiedImageError, OSError, ValueError) as e:
            raise FigureValidationError(f"corrupt JPEG: {e}") from e
        return ValidatedImage(
            mime="image/jpeg", width_px=int(w), height_px=int(h), byte_size=len(data)
        )

    # SVG
    if _is_svg(data):
        return ValidatedImage(
            mime="image/svg+xml", width_px=None, height_px=None, byte_size=len(data)
        )

    raise FigureValidationError(
        "unsupported image format — only PNG, JPEG, and SVG are accepted"
    )
