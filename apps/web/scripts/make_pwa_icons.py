#!/usr/bin/env python3
"""Phase M0.2 — generate placeholder PWA icons.

Mirrors the Electron app's "RA" tile so the desktop app and the
phone home-screen icon look identical until a designed icon lands.

Outputs (relative to apps/web/):
    public/icons/icon-192.png       (PWA manifest, "any maskable")
    public/icons/icon-512.png       (PWA manifest, "any maskable")
    public/icons/apple-touch-icon.png (180x180 — iOS home screen)

Run from apps/web/ ::

    python scripts/make_pwa_icons.py

Self-contained: only Pillow (already in the backend venv) is required.
No paid services, no network calls.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# Brand colour — must match the Electron app + manifest theme_color so
# the platform chrome (iOS status bar, Android task switcher) matches.
BG_COLOUR = "#0F1117"
FG_COLOUR = "#FFFFFF"

WEB_DIR = Path(__file__).resolve().parent.parent
ICONS_DIR = WEB_DIR / "public" / "icons"

# (size_px, output_filename) tuples.
OUTPUTS: list[tuple[int, str]] = [
    (192, "icon-192.png"),
    (512, "icon-512.png"),
    (180, "apple-touch-icon.png"),
]


def _font_for(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Pick a system bold font that scales well to the tile size."""
    candidates = [
        # macOS
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "/System/Library/Fonts/HelveticaNeue.ttc",
        # Linux
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        # Windows (cross-build scenarios)
        "C:/Windows/Fonts/arialbd.ttf",
    ]
    font_size = int(size * 0.45)
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, font_size)
            except OSError:
                continue
    return ImageFont.load_default()


def _rounded_tile(size: int) -> Image.Image:
    """Render a single PNG tile at ``size`` px."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # iOS ignores the alpha channel and clips the icon to its own
    # rounded-rectangle mask. Android (maskable purpose) needs the safe
    # zone to fit inside an 80% inscribed circle, which a uniform fill +
    # centred "RA" easily satisfies.
    radius = max(2, size // 5)
    draw.rounded_rectangle(
        (0, 0, size, size), radius=radius, fill=BG_COLOUR
    )
    text = "RA"
    font = _font_for(size)
    # Pillow >= 8 returns (left, top, right, bottom) for textbbox.
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    cx = (size - text_w) / 2 - bbox[0]
    cy = (size - text_h) / 2 - bbox[1]
    draw.text((cx, cy), text, fill=FG_COLOUR, font=font)
    return img


def main() -> int:
    ICONS_DIR.mkdir(parents=True, exist_ok=True)
    for size, filename in OUTPUTS:
        out = ICONS_DIR / filename
        _rounded_tile(size).save(out, format="PNG")
        rel = out.relative_to(WEB_DIR)
        print(f"wrote {rel} ({size}x{size})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
