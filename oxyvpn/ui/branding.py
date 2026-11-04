"""Logo loading with graceful fallback.

Drop photo.png next to main.py. The mark is rendered oversized inside its
canvas so the image's baked-in edge is clipped away and only the mark shows.
If the file is missing the UI draws its own vector mark.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path

from . import theme

NAMES = ("photo.png", "photo.jpg", "photo.jpeg", "photo.webp",
         "logo.png", "logo.jpg", "logo.jpeg")

OVERSCAN = 1.16

_cache = {}


def _candidates():
    here = Path(__file__).resolve().parent
    roots = [here, here.parent, here.parent.parent, Path.cwd()]
    seen, found = [], []
    for root in roots:
        for name in NAMES:
            path = root / name
            if path in seen:
                continue
            seen.append(path)
            if path.is_file():
                found.append(path)
    return found


def _resize(path, size):
    try:
        image = tk.PhotoImage(file=str(path))
    except tk.TclError:
        image = None
    if image is not None:
        width = image.width()
        if width > size:
            factor = max(1, int(round(width / float(size))))
            image = image.subsample(factor, factor)
        return image
    try:
        from PIL import Image, ImageTk
    except Exception:
        return None
    try:
        pil = Image.open(str(path)).convert("RGBA")
        pil = pil.resize((size, size), Image.LANCZOS)
        return ImageTk.PhotoImage(pil)
    except Exception:
        return None


def logo(master, size=28):
    """Return a cached logo image, or None when no asset exists."""
    render = int(round(size * OVERSCAN))
    for path in _candidates():
        key = (str(path), render)
        if key in _cache:
            return _cache[key]
        image = _resize(path, render)
        if image is not None:
            _cache[key] = image
            return image
    return None


def draw(canvas, cx, cy, size, bg=None):
    """Paint the mark centred on a canvas of exactly `size` pixels."""
    image = logo(canvas, size)
    half = size / 2.0
    radius = size * 0.27

    if image is None:
        canvas.create_oval(cx - half, cy - half, cx + half, cy + half,
                           fill=bg or theme.ACCENT_DIM, outline=theme.ACCENT, width=1)
        canvas.create_text(cx, cy, text="O", fill=theme.ACCENT,
                           font=theme.f(max(8, int(size * 0.5)), "bold"))
        return False

    canvas.create_rectangle(cx - half, cy - half, cx + half, cy + half,
                            fill=theme.TILE, outline="")
    canvas.create_image(cx, cy, image=image)
    return True