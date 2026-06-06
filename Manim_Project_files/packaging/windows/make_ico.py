#!/usr/bin/env python3
"""Generate the ManimStudio Windows icon (manimstudio.ico).

Reuses the committed Atom One Dark PNG artwork from the .deb packaging
(`packaging/deb/manimstudio.png`) as the single source of truth and packs it
into a multi-resolution .ico (16/24/32/48/64/128/256) for Start Menu, desktop,
and Explorer use. Falls back to regenerating the PNG via the deb make_icon.py
if it is missing. Output path is the first CLI arg (default: manimstudio.ico
next to this script). Requires Pillow.
"""
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
PNG = os.path.join(HERE, "..", "deb", "manimstudio.png")
SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def _ensure_png() -> str:
    if os.path.isfile(PNG):
        return PNG
    # Regenerate from the deb icon script if the committed PNG is absent.
    sys.path.insert(0, os.path.join(HERE, "..", "deb"))
    import make_icon  # type: ignore

    make_icon.make(PNG)
    return PNG


def make(out_path: str) -> None:
    src = Image.open(_ensure_png()).convert("RGBA")
    # Pillow downsamples to each requested size when writing the .ico.
    src.save(out_path, format="ICO", sizes=SIZES)
    print(f"wrote {out_path} ({len(SIZES)} sizes, up to {SIZES[-1][0]}px)")


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "manimstudio.ico")
    make(out)
