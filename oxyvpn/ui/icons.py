"""Vector icons drawn directly on a canvas."""

from __future__ import annotations

import math


def power(canvas, cx, cy, size, colour, width=3):
    r = size / 2.0
    canvas.create_arc(cx - r, cy - r + size * 0.10, cx + r, cy + r + size * 0.10,
                      start=58, extent=244, style="arc", outline=colour, width=width)
    canvas.create_line(cx, cy - r - size * 0.10, cx, cy + size * 0.06,
                       fill=colour, width=width)


def shield(canvas, cx, cy, size, colour, width=2):
    w = size * 0.80
    top = cy - size * 0.52
    canvas.create_polygon([
        cx, top,
        cx + w / 2, top + size * 0.20,
        cx + w / 2, cy + size * 0.06,
        cx, cy + size * 0.54,
        cx - w / 2, cy + size * 0.06,
        cx - w / 2, top + size * 0.20,
    ], outline=colour, fill="", width=width)


def globe(canvas, cx, cy, size, colour, width=2):
    r = size / 2.0
    canvas.create_oval(cx - r, cy - r, cx + r, cy + r, outline=colour, width=width)
    canvas.create_oval(cx - r * 0.45, cy - r, cx + r * 0.45, cy + r,
                       outline=colour, width=width)
    canvas.create_line(cx - r, cy, cx + r, cy, fill=colour, width=width)
    canvas.create_arc(cx - r, cy - r * 0.5, cx + r, cy + r * 0.5,
                      start=0, extent=180, style="arc", outline=colour, width=width)


def gear(canvas, cx, cy, size, colour, width=2):
    r = size / 2.0
    inner = r * 0.44
    for i in range(8):
        angle = math.radians(i * 45)
        canvas.create_line(cx + math.cos(angle) * inner, cy + math.sin(angle) * inner,
                           cx + math.cos(angle) * r, cy + math.sin(angle) * r,
                           fill=colour, width=width)
    canvas.create_oval(cx - inner, cy - inner, cx + inner, cy + inner,
                       outline=colour, width=width)


def terminal(canvas, cx, cy, size, colour, width=2):
    w = size * 0.9
    h = size * 0.74
    canvas.create_rectangle(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2,
                            outline=colour, width=width)
    canvas.create_line(cx - w * 0.28, cy - h * 0.16, cx - w * 0.06, cy,
                       fill=colour, width=width)
    canvas.create_line(cx - w * 0.28, cy + h * 0.16, cx - w * 0.06, cy,
                       fill=colour, width=width)
    canvas.create_line(cx + w * 0.06, cy + h * 0.22, cx + w * 0.30, cy + h * 0.22,
                       fill=colour, width=width)


def search(canvas, cx, cy, size, colour, width=2):
    r = size * 0.34
    canvas.create_oval(cx - r, cy - r, cx + r, cy + r, outline=colour, width=width)
    canvas.create_line(cx + r * 0.72, cy + r * 0.72, cx + r * 1.5, cy + r * 1.5,
                       fill=colour, width=width)


def bolt(canvas, cx, cy, size, colour, width=2):
    h = size * 0.5
    canvas.create_polygon([
        cx + h * 0.30, cy - h,
        cx - h * 0.55, cy + h * 0.10,
        cx - h * 0.05, cy + h * 0.10,
        cx - h * 0.30, cy + h,
        cx + h * 0.55, cy - h * 0.10,
        cx + h * 0.05, cy - h * 0.10,
    ], outline=colour, fill="", width=width)


def arrow_down(canvas, cx, cy, size, colour, width=2):
    r = size * 0.42
    canvas.create_line(cx, cy - r, cx, cy + r * 0.75, fill=colour, width=width)
    canvas.create_line(cx - r * 0.55, cy + r * 0.22, cx, cy + r * 0.78,
                       fill=colour, width=width)
    canvas.create_line(cx + r * 0.55, cy + r * 0.22, cx, cy + r * 0.78,
                       fill=colour, width=width)


def arrow_up(canvas, cx, cy, size, colour, width=2):
    r = size * 0.42
    canvas.create_line(cx, cy + r, cx, cy - r * 0.75, fill=colour, width=width)
    canvas.create_line(cx - r * 0.55, cy - r * 0.22, cx, cy - r * 0.78,
                       fill=colour, width=width)
    canvas.create_line(cx + r * 0.55, cy - r * 0.22, cx, cy - r * 0.78,
                       fill=colour, width=width)


def clock(canvas, cx, cy, size, colour, width=2):
    r = size * 0.44
    canvas.create_oval(cx - r, cy - r, cx + r, cy + r, outline=colour, width=width)
    canvas.create_line(cx, cy - r * 0.55, cx, cy, fill=colour, width=width)
    canvas.create_line(cx, cy, cx + r * 0.48, cy + r * 0.30, fill=colour, width=width)


def check(canvas, cx, cy, size, colour, width=2):
    r = size * 0.4
    canvas.create_line(cx - r, cy + r * 0.05, cx - r * 0.18, cy + r * 0.72,
                       fill=colour, width=width)
    canvas.create_line(cx - r * 0.18, cy + r * 0.72, cx + r, cy - r * 0.7,
                       fill=colour, width=width)


def cross(canvas, cx, cy, size, colour, width=2):
    r = size * 0.36
    canvas.create_line(cx - r, cy - r, cx + r, cy + r, fill=colour, width=width)
    canvas.create_line(cx + r, cy - r, cx - r, cy + r, fill=colour, width=width)


def lock(canvas, cx, cy, size, colour, width=2):
    w = size * 0.62
    h = size * 0.48
    top = cy - size * 0.10
    canvas.create_rectangle(cx - w / 2, top, cx + w / 2, top + h,
                            outline=colour, width=width)
    canvas.create_arc(cx - w * 0.34, top - h * 0.86, cx + w * 0.34, top + h * 0.24,
                      start=0, extent=180, style="arc", outline=colour, width=width)


def key(canvas, cx, cy, size, colour, width=2):
    r = size * 0.22
    canvas.create_oval(cx - size * 0.44, cy - r, cx - size * 0.44 + r * 2, cy + r,
                       outline=colour, width=width)
    canvas.create_line(cx - size * 0.24, cy, cx + size * 0.44, cy, fill=colour, width=width)
    canvas.create_line(cx + size * 0.24, cy, cx + size * 0.24, cy + r * 1.1,
                       fill=colour, width=width)
    canvas.create_line(cx + size * 0.42, cy, cx + size * 0.42, cy + r * 0.9,
                       fill=colour, width=width)


def folder(canvas, cx, cy, size, colour, width=2):
    w = size * 0.82
    h = size * 0.56
    canvas.create_line(cx - w / 2, cy - h / 2, cx - w / 6, cy - h / 2,
                       cx - w / 12, cy - h / 2 + h * 0.22,
                       cx + w / 2, cy - h / 2 + h * 0.22,
                       cx + w / 2, cy + h / 2,
                       cx - w / 2, cy + h / 2,
                       cx - w / 2, cy - h / 2,
                       fill=colour, width=width, joinstyle="round")


def refresh(canvas, cx, cy, size, colour, width=2):
    r = size * 0.40
    canvas.create_arc(cx - r, cy - r, cx + r, cy + r, start=35, extent=290,
                      style="arc", outline=colour, width=width)
    canvas.create_line(cx + r * 0.62, cy - r * 0.86, cx + r * 1.02, cy - r * 0.52,
                       fill=colour, width=width)
    canvas.create_line(cx + r * 1.02, cy - r * 0.52, cx + r * 0.60, cy - r * 0.30,
                       fill=colour, width=width)


def info(canvas, cx, cy, size, colour, width=2):
    r = size * 0.44
    canvas.create_oval(cx - r, cy - r, cx + r, cy + r, outline=colour, width=width)
    canvas.create_line(cx, cy - r * 0.42, cx, cy - r * 0.40, fill=colour, width=width + 1)
    canvas.create_line(cx, cy - r * 0.08, cx, cy + r * 0.50, fill=colour, width=width)


def dot(canvas, cx, cy, size, colour, width=2):
    r = size * 0.22
    canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill=colour, outline=colour)


ICONS = {
    "shield": shield,
    "globe": globe,
    "gear": gear,
    "terminal": terminal,
    "power": power,
    "search": search,
    "bolt": bolt,
    "down": arrow_down,
    "up": arrow_up,
    "clock": clock,
    "check": check,
    "cross": cross,
    "lock": lock,
    "key": key,
    "folder": folder,
    "refresh": refresh,
    "info": info,
    "dot": dot,
}