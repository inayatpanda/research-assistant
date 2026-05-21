#!/usr/bin/env python3
"""Phase E1.3 — Generate placeholder app icons.

The brand identity is deferred to a later phase. For now we emit a
"RA" tile with the sidebar's dark background colour and rounded
corners, in every size electron-builder asks for.

Outputs:
    build/icons/16.png .. 1024.png
    build/icons/icon.icns   (macOS bundle; requires `iconutil` or icnsutil)
    build/icons/icon.ico    (Windows multi-resolution)

The script is self-contained: it only depends on Pillow (already in the
backend venv) and the macOS-only ``iconutil`` binary for ``.icns``. If
``iconutil`` is unavailable we still write the PNGs + the ``.ico`` so
electron-builder can produce a Mac DMG with a fallback (electron-builder
will auto-convert the largest PNG when neither path exists).

Run from the desktop directory::

    python scripts/make_placeholder_icons.py
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# Brand colour — same as the sidebar background in apps/web/src/index.css.
BG_COLOUR = "#0F1117"
FG_COLOUR = "#FFFFFF"

DESKTOP_DIR = Path(__file__).resolve().parent.parent
ICONS_DIR = DESKTOP_DIR / "build" / "icons"

# Sizes electron-builder + macOS asks for. 1024 is required for App Store
# submission down the line, even though we don't ship there in E1.
SIZES = [16, 32, 64, 128, 256, 512, 1024]


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


def _write_pngs() -> dict[int, Path]:
    ICONS_DIR.mkdir(parents=True, exist_ok=True)
    paths: dict[int, Path] = {}
    for size in SIZES:
        out = ICONS_DIR / f"{size}.png"
        _rounded_tile(size).save(out)
        paths[size] = out
        print(f"wrote {out.relative_to(DESKTOP_DIR)}")
    # electron-builder picks `icon.png` for some platforms.
    fallback = ICONS_DIR / "icon.png"
    shutil.copyfile(paths[512], fallback)
    print(f"wrote {fallback.relative_to(DESKTOP_DIR)}")
    # D1.2 — Linux AppImage build references ``icon-512.png`` directly
    # (electron-builder won't accept the generic ``icon.png`` as the
    # Linux icon in our config). Copy from the 512 master.
    linux_icon = ICONS_DIR / "icon-512.png"
    shutil.copyfile(paths[512], linux_icon)
    print(f"wrote {linux_icon.relative_to(DESKTOP_DIR)}")
    return paths


def _write_ico(paths: dict[int, Path]) -> None:
    """Pack several PNGs into a multi-resolution Windows ``.ico``."""
    base = paths[256]
    img = Image.open(base)
    sizes = [(s, s) for s in (16, 32, 48, 64, 128, 256)]
    out = ICONS_DIR / "icon.ico"
    img.save(out, format="ICO", sizes=sizes)
    print(f"wrote {out.relative_to(DESKTOP_DIR)}")


def _try_icnsutil(paths: dict[int, Path]) -> bool:
    try:
        import icnsutil  # type: ignore
    except Exception:
        return False
    # icnsutil API: IcnsFile().add_media(media_type, path) — but the
    # simpler entry is the CLI: icnsutil compose icon.icns 16.png 32.png ...
    out = ICONS_DIR / "icon.icns"
    icns = icnsutil.IcnsFile()
    type_map = {
        16: "is32",
        32: "il32",
        64: "ic12",
        128: "ic07",
        256: "ic08",
        512: "ic09",
        1024: "ic10",
    }
    for size, key in type_map.items():
        if size in paths:
            try:
                icns.add_media(key=key, file=str(paths[size]))
            except Exception:
                pass
    try:
        icns.write(str(out))
        print(f"wrote {out.relative_to(DESKTOP_DIR)} (via icnsutil)")
        return True
    except Exception as exc:
        print(f"icnsutil failed: {exc}", file=sys.stderr)
        return False


def _try_iconutil(paths: dict[int, Path]) -> bool:
    """Use macOS ``iconutil`` to compose an `.icns`."""
    if sys.platform != "darwin" or not shutil.which("iconutil"):
        return False
    with tempfile.TemporaryDirectory() as td:
        iconset = Path(td) / "icon.iconset"
        iconset.mkdir()
        # iconutil's required naming convention.
        mapping = {
            16: ["icon_16x16.png"],
            32: ["icon_16x16@2x.png", "icon_32x32.png"],
            64: ["icon_32x32@2x.png"],
            128: ["icon_128x128.png"],
            256: ["icon_128x128@2x.png", "icon_256x256.png"],
            512: ["icon_256x256@2x.png", "icon_512x512.png"],
            1024: ["icon_512x512@2x.png"],
        }
        for size, names in mapping.items():
            if size not in paths:
                continue
            for name in names:
                shutil.copyfile(paths[size], iconset / name)
        out = ICONS_DIR / "icon.icns"
        try:
            subprocess.run(
                ["iconutil", "-c", "icns", "-o", str(out), str(iconset)],
                check=True,
            )
            print(f"wrote {out.relative_to(DESKTOP_DIR)} (via iconutil)")
            return True
        except subprocess.CalledProcessError as exc:
            print(f"iconutil failed: {exc}", file=sys.stderr)
            return False


def main() -> int:
    paths = _write_pngs()
    _write_ico(paths)
    if not _try_iconutil(paths) and not _try_icnsutil(paths):
        print(
            "warn: no .icns generator available (iconutil/icnsutil missing) — "
            "electron-builder will fall back to the largest PNG.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
