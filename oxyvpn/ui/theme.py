"""Design tokens: palette, elevation, spacing, motion, typography."""

from __future__ import annotations

BG = "#07080c"
BG_ALT = "#0a0c12"
BG_SUNKEN = "#050609"
SURFACE_LOW = "#0c0e14"
SURFACE = "#101319"
SURFACE_HI = "#151922"
SURFACE_ACTIVE = "#1b212c"
ELEVATED = "#1f2531"

BORDER = "#1a1f29"
BORDER_HI = "#252c39"
HAIRLINE = "#151a23"

TILE = "#0b1020"

TEXT = "#f2f5fa"
TEXT_DIM = "#a3aec1"
TEXT_MUTED = "#7c8699"
TEXT_FAINT = "#5b6478"

ACCENT = "#4d8dff"
ACCENT_HOVER = "#6fa2ff"
ACCENT_PRESS = "#3d78e0"
ACCENT_DIM = "#122340"
ACCENT_SOFT = "#1a3054"
CYAN = "#2fd9c8"

GREEN = "#2fd98a"
GREEN_DIM = "#0d3526"
GREEN_SOFT = "#123f2e"
AMBER = "#f5b83d"
AMBER_DIM = "#3a2c0d"
AMBER_SOFT = "#463509"
RED = "#f4626f"
RED_DIM = "#3a1419"
RED_SOFT = "#4d1b21"
VIOLET = "#a78bfa"
VIOLET_DIM = "#2a1f4d"
VIOLET_SOFT = "#382a63"

FONT = "Segoe UI"
MONO = "Consolas"

S8, S9, S10, S11, S13, S15, S18, S22, S28 = 8, 9, 10, 11, 13, 15, 18, 22, 28

SP1, SP2, SP3, SP4, SP5, SP6, SP8 = 4, 8, 12, 16, 20, 24, 32

RADIUS_XS = 6
RADIUS_SM = 8
RADIUS = 12
RADIUS_LG = 16

TICK_MS = 33
DRAG_EASE = 0.18
TOAST_MS = 3600
DRAIN_MS = 60

SEVERITY_COLOURS = {
    "critical": RED,
    "high": "#ff8a4c",
    "medium": AMBER,
    "low": ACCENT,
    "info": TEXT_FAINT,
}


def _rgb(value: str):
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def _hex(channels):
    return "#%02x%02x%02x" % tuple(
        max(0, min(255, int(round(c)))) for c in channels)


def mix(first: str, second: str, amount: float) -> str:
    a, b = _rgb(first), _rgb(second)
    return _hex(tuple(a[i] + (b[i] - a[i]) * amount for i in range(3)))


def lighten(colour: str, amount: float = 0.14) -> str:
    return mix(colour, "#ffffff", amount)


def darken(colour: str, amount: float = 0.14) -> str:
    return mix(colour, "#000000", amount)


def fade(colour: str, background: str, amount: float) -> str:
    return mix(background, colour, amount)


def f(size=S10, weight="normal"):
    return (FONT, size, weight)


def m(size=S9):
    return (MONO, size)


def severity_colour(value):
    return SEVERITY_COLOURS.get(str(value).lower(), TEXT_FAINT)