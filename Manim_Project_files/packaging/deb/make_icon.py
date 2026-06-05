#!/usr/bin/env python3
"""Generate the ManimStudio app icon (256x256 PNG) in the Atom One Dark palette.

A rounded dark square with a centered "play" triangle — the render/animate
motif — filled with the app's blue→teal accent. Output path is the first CLI
arg (default: manimstudio.png next to this script). Requires Pillow.
"""
import sys
import os
from PIL import Image, ImageDraw

SIZE = 256
BG_TOP    = (33, 37, 43)     # #21252b
BG_BOTTOM = (40, 44, 52)     # #282c34  (Atom One Dark editor bg)
BORDER    = (60, 66, 77)     # subtle raised edge
ACCENT_A  = (97, 175, 239)   # #61afef  blue
ACCENT_B  = (86, 182, 194)   # #56b6c2  teal


def _rounded_mask(size: int, radius: int) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    return mask


def _vertical_gradient(size, top, bottom) -> Image.Image:
    grad = Image.new("RGB", (1, size))
    for y in range(size):
        t = y / (size - 1)
        grad.putpixel((0, y), tuple(
            round(top[i] + (bottom[i] - top[i]) * t) for i in range(3)
        ))
    return grad.resize((size, size))


def make(out_path: str) -> None:
    # Background: vertical gradient clipped to a rounded square.
    bg = _vertical_gradient(SIZE, BG_TOP, BG_BOTTOM).convert("RGBA")
    mask = _rounded_mask(SIZE, radius=52)
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    img.paste(bg, (0, 0), mask)

    # Thin inner border for a crisp edge on light and dark desktops.
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([2, 2, SIZE - 3, SIZE - 3], radius=50,
                        outline=BORDER, width=3)

    # Play triangle, optically centered (nudged right of true center).
    tri = [(98, 74), (98, 182), (186, 128)]
    # Build the triangle on its own layer with a blue→teal horizontal gradient.
    tri_layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    ImageDraw.Draw(tri_layer).polygon(tri, fill=(255, 255, 255, 255))
    hgrad = Image.new("RGBA", (SIZE, 1))
    for x in range(SIZE):
        t = x / (SIZE - 1)
        hgrad.putpixel((x, 0), tuple(
            round(ACCENT_A[i] + (ACCENT_B[i] - ACCENT_A[i]) * t) for i in range(3)
        ) + (255,))
    hgrad = hgrad.resize((SIZE, SIZE))
    tri_color = Image.composite(hgrad, Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0)),
                                tri_layer.split()[3])
    img.alpha_composite(tri_color)

    img.save(out_path, "PNG")
    print(f"wrote {out_path} ({SIZE}x{SIZE})")


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "manimstudio.png")
    make(out)
