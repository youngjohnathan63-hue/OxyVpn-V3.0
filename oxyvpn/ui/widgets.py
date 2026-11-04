"""Reusable themed widgets.

NOTE: never assign to self._w - Tkinter stores the widget's Tcl path there.
"""

from __future__ import annotations

import tkinter as tk

from . import branding, theme
from .icons import ICONS

FLAG_BANDS = {
    "us": ("h", ["#b22234", "#ffffff", "#b22234", "#ffffff", "#b22234"]),
    "gb": ("cross", ["#012169", "#ffffff"]),
    "de": ("h", ["#000000", "#dd0000", "#ffce00"]),
    "fr": ("v", ["#0055a4", "#ffffff", "#ef4135"]),
    "nl": ("h", ["#ae1c28", "#ffffff", "#21468b"]),
    "jp": ("dot", ["#ffffff", "#bc002d"]),
    "ca": ("v", ["#d52b1e", "#ffffff", "#d52b1e"]),
    "it": ("v", ["#009246", "#ffffff", "#ce2b37"]),
    "ie": ("v", ["#169b62", "#ffffff", "#ff883e"]),
    "be": ("v", ["#000000", "#fdda24", "#ef3340"]),
    "at": ("h", ["#ed2939", "#ffffff", "#ed2939"]),
    "es": ("h", ["#aa151b", "#f1bf00", "#aa151b"]),
    "pt": ("v", ["#046a38", "#da291c"]),
    "pl": ("h", ["#ffffff", "#dc143c"]),
    "cz": ("h", ["#ffffff", "#d7141a"]),
    "sk": ("h", ["#ffffff", "#0b4ea2", "#ee1c25"]),
    "hu": ("h", ["#ce2939", "#ffffff", "#477050"]),
    "ro": ("v", ["#002b7f", "#fcd116", "#ce1126"]),
    "bg": ("h", ["#ffffff", "#00966e", "#d62612"]),
    "gr": ("h", ["#0d5eaf", "#ffffff", "#0d5eaf"]),
    "se": ("cross", ["#006aa7", "#fecc00"]),
    "no": ("cross", ["#ba0c2f", "#ffffff"]),
    "dk": ("cross", ["#c8102e", "#ffffff"]),
    "fi": ("cross", ["#ffffff", "#002f6c"]),
    "is": ("cross", ["#02529c", "#ffffff"]),
    "ch": ("cross", ["#d52b1e", "#ffffff"]),
    "ua": ("h", ["#0057b7", "#ffd700"]),
    "tr": ("dot", ["#e30a17", "#ffffff"]),
    "br": ("dot", ["#009c3b", "#ffdf00"]),
    "ar": ("h", ["#74acdf", "#ffffff", "#74acdf"]),
    "mx": ("v", ["#006847", "#ffffff", "#ce1126"]),
    "cl": ("h", ["#ffffff", "#d52b1e"]),
    "co": ("h", ["#fcd116", "#003893", "#ce1126"]),
    "za": ("h", ["#007a4d", "#ffffff", "#de3831"]),
    "in": ("h", ["#ff9933", "#ffffff", "#138808"]),
    "sg": ("h", ["#ed2939", "#ffffff"]),
    "hk": ("dot", ["#de2910", "#ffffff"]),
    "kr": ("dot", ["#ffffff", "#cd2e3a"]),
    "tw": ("dot", ["#fe0000", "#000095"]),
    "th": ("h", ["#a51931", "#f4f5f8", "#2d2a4a"]),
    "my": ("h", ["#cc0001", "#ffffff", "#cc0001"]),
    "id": ("h", ["#ce1126", "#ffffff"]),
    "ph": ("h", ["#0038a8", "#ce1126"]),
    "vn": ("dot", ["#da251d", "#ffff00"]),
    "nz": ("cross", ["#00247d", "#ffffff"]),
    "au": ("cross", ["#00247d", "#ffffff"]),
    "il": ("cross", ["#ffffff", "#0038b8"]),
    "ae": ("v", ["#00732f", "#ffffff", "#000000"]),
    "ng": ("v", ["#008751", "#ffffff", "#008751"]),
    "ke": ("h", ["#000000", "#bb0000", "#006600"]),
    "eg": ("h", ["#ce1126", "#ffffff", "#000000"]),
    "ma": ("dot", ["#c1272d", "#006233"]),
    "md": ("v", ["#003da5", "#ffd200", "#cc092f"]),
    "rs": ("h", ["#c6363c", "#0c4076", "#ffffff"]),
    "hr": ("h", ["#ff0000", "#ffffff", "#171796"]),
    "si": ("h", ["#ffffff", "#005da4", "#ed1c24"]),
    "cy": ("dot", ["#ffffff", "#d57800"]),
    "mt": ("v", ["#ffffff", "#cf142b"]),
    "ge": ("cross", ["#ffffff", "#ff0000"]),
    "am": ("h", ["#d90012", "#0033a0", "#f2a800"]),
    "kz": ("dot", ["#00afca", "#fec50c"]),
    "pk": ("v", ["#01411c", "#ffffff"]),
    "bd": ("dot", ["#006a4e", "#f42a41"]),
    "lk": ("dot", ["#8d153a", "#ffb700"]),
    "cr": ("h", ["#002b7f", "#ffffff", "#ce1126"]),
}


def round_rect(canvas, x1, y1, x2, y2, radius, fill, outline="", width=1, tags=None):
    radius = max(0, min(radius, abs(x2 - x1) / 2.0, abs(y2 - y1) / 2.0))
    points = [
        x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
        x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
        x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, splinesteps=24,
                                 fill=fill, outline=outline, width=width, tags=tags)


def draw_flag(canvas, cx, cy, width, height, code, bg=None):
    """Draw a simplified flag badge. Falls back to the country code."""
    bg = bg or theme.SURFACE_HI
    x1, y1 = cx - width / 2.0, cy - height / 2.0
    x2, y2 = cx + width / 2.0, cy + height / 2.0
    spec = FLAG_BANDS.get((code or "").lower())

    if spec is None:
        round_rect(canvas, x1, y1, x2, y2, 4, bg, theme.BORDER_HI, 1)
        canvas.create_text(cx, cy, text=(code or "??").upper()[:2],
                           fill=theme.TEXT_DIM, font=theme.f(7, "bold"))
        return False

    kind, bands = spec
    if kind == "h":
        step = height / float(len(bands))
        for index, colour in enumerate(bands):
            canvas.create_rectangle(x1, y1 + index * step, x2,
                                    y1 + (index + 1) * step, fill=colour, outline="")
    elif kind == "v":
        step = width / float(len(bands))
        for index, colour in enumerate(bands):
            canvas.create_rectangle(x1 + index * step, y1, x1 + (index + 1) * step,
                                    y2, fill=colour, outline="")
    elif kind == "dot":
        canvas.create_rectangle(x1, y1, x2, y2, fill=bands[0], outline="")
        radius = height * 0.28
        canvas.create_oval(cx - radius, cy - radius, cx + radius, cy + radius,
                           fill=bands[1], outline="")
    else:
        canvas.create_rectangle(x1, y1, x2, y2, fill=bands[0], outline="")
        canvas.create_line(cx, y1 + 2, cx, y2 - 2, fill=bands[1], width=2)
        canvas.create_line(x1 + 2, cy, x2 - 2, cy, fill=bands[1], width=2)

    round_rect(canvas, x1, y1, x2, y2, 4, "", theme.BORDER_HI, 1)
    return True


class Eyebrow(tk.Label):
    def __init__(self, master, text, bg=None):
        bg = bg or master["bg"]
        super().__init__(master, text=text.upper(), bg=bg, fg=theme.TEXT_FAINT,
                         font=theme.f(theme.S8, "bold"), anchor="w")


class RadialBackdrop(tk.Canvas):
    """Soft radial wash used behind the connection control."""

    def __init__(self, master, bg=None, colour=theme.ACCENT):
        bg = bg or theme.BG
        super().__init__(master, bg=bg, highlightthickness=0, bd=0)
        self._bg = bg
        self._colour = colour
        self.bind("<Configure>", lambda e: self.redraw())

    def set_colour(self, colour):
        self._colour = colour
        self.redraw()

    def redraw(self):
        self.delete("all")
        width = self.winfo_width()
        height = self.winfo_height()
        if width < 10 or height < 10:
            return
        cx = width / 2.0
        cy = height * 0.44
        outer = min(width, height) * 0.78
        steps = 26
        for index in range(steps, 0, -1):
            t = index / float(steps)
            radius = outer * t
            amount = 0.085 * (1.0 - t) ** 1.5 + 0.010
            self.create_oval(cx - radius, cy - radius, cx + radius, cy + radius,
                             fill=theme.fade(self._colour, self._bg, amount),
                             outline="")


class PhaseTracker(tk.Canvas):
    """Six-step handshake indicator."""

    PHASES = ["Prepare", "Connect", "Auth", "Config", "Address", "Up"]

    def __init__(self, master, bg=None):
        bg = bg or theme.BG
        super().__init__(master, height=24, bg=bg, highlightthickness=0, bd=0)
        self._bg = bg
        self._index = -1
        self._colour = theme.ACCENT
        self.bind("<Configure>", lambda e: self._draw())

    def set_phase(self, index, colour=None):
        self._index = index
        self._colour = colour or theme.ACCENT
        self._draw()

    def _draw(self):
        self.delete("all")
        width = self.winfo_width()
        if width < 60:
            return
        count = len(self.PHASES)
        span = min(width - 48, 268)
        gap = span / float(count - 1)
        left = (width - span) / 2.0
        y = 11
        for index in range(count):
            x = left + index * gap
            if index < self._index:
                colour = theme.GREEN
            elif index == self._index:
                colour = self._colour
            else:
                colour = theme.SURFACE_ACTIVE
            if index:
                previous = left + (index - 1) * gap
                line = theme.GREEN if index <= self._index else theme.HAIRLINE
                self.create_line(previous + 5, y, x - 5, y, fill=line, width=2)
            radius = 4 if index == self._index else 3
            self.create_oval(x - radius, y - radius, x + radius, y + radius,
                             fill=colour, outline=colour)


class SessionCard(tk.Canvas):
    """Compact live session readout for the sidebar footer."""

    HEIGHT = 56

    def __init__(self, master, bg=None):
        bg = bg or theme.BG_ALT
        super().__init__(master, height=self.HEIGHT, bg=bg,
                         highlightthickness=0, bd=0)
        self._bg = bg
        self._state = "idle"
        self._title = "No session"
        self._uptime = 0.0
        self.bind("<Configure>", lambda e: self._draw())
        self._draw()

    def update_state(self, state, title="", uptime=None):
        self._state = state
        self._title = title or "No session"
        if uptime is not None:
            self._uptime = uptime
        self._draw()

    def _colour(self):
        return {"connected": theme.GREEN,
                "connecting": theme.ACCENT,
                "failed": theme.RED}.get(self._state, theme.TEXT_FAINT)

    def _draw(self):
        self.delete("all")
        width = self.winfo_width()
        if width < 40:
            return
        colour = self._colour()
        round_rect(self, 1, 1, width - 2, self.HEIGHT - 2, theme.RADIUS,
                   theme.SURFACE, theme.BORDER, 1)
        self.create_oval(13, 15, 21, 23, fill=colour, outline=colour)
        text = self._title
        if len(text) > 20:
            text = text[:19] + "\u2026"
        self.create_text(28, 19, text=text, fill=theme.TEXT,
                         font=theme.f(theme.S9, "bold"), anchor="w")
        if self._state == "connected":
            stamp = "%02d:%02d:%02d" % (int(self._uptime // 3600),
                                        int((self._uptime % 3600) // 60),
                                        int(self._uptime % 60))
            label = stamp
        else:
            label = {"connecting": "negotiating", "failed": "failed"}.get(
                self._state, "idle")
        self.create_text(13, 39, text=label, fill=theme.TEXT_FAINT,
                         font=theme.m(theme.S8), anchor="w")


class Card(tk.Frame):
    """Bordered panel with optional header. Body is where content goes."""

    def __init__(self, master, pad=16, radius=theme.RADIUS, fill=None, bg=None,
                 title=None, subtitle=None, tone=None):
        fill = fill or theme.SURFACE
        bg = bg or master["bg"]
        super().__init__(master, bg=bg)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)

        self.body = tk.Frame(self.canvas, bg=fill)
        self._win = self.canvas.create_window(pad, pad, window=self.body, anchor="nw")
        self._pad = pad
        self._radius = radius
        self._fill = fill
        self._bg = bg
        self._border = tone or theme.BORDER
        self._hover = False

        self.body.bind("<Configure>", self._sync)
        self.canvas.bind("<Configure>", self._on_canvas)
        for widget in (self.canvas, self.body):
            widget.bind("<Enter>", self._enter)
            widget.bind("<Leave>", self._leave)

        if title:
            head = tk.Frame(self.body, bg=fill)
            head.pack(fill="x", pady=(0, 10))
            tk.Label(head, text=title.upper(), bg=fill, fg=theme.TEXT_MUTED,
                     font=theme.f(theme.S8, "bold"), anchor="w").pack(fill="x")
            if subtitle:
                tk.Label(head, text=subtitle, bg=fill, fg=theme.TEXT_FAINT,
                         font=theme.f(theme.S9), anchor="w",
                         justify="left", wraplength=520).pack(fill="x", pady=(2, 0))

    def _enter(self, _event=None):
        self._hover = True
        self._draw()

    def _leave(self, _event=None):
        self._hover = False
        self._draw()

    def _on_canvas(self, event):
        self.canvas.itemconfigure(self._win, width=max(1, event.width - 2 * self._pad))
        self._draw()

    def _sync(self, _event=None):
        needed = self.body.winfo_reqheight() + 2 * self._pad
        if abs(self.canvas.winfo_height() - needed) > 1:
            self.canvas.configure(height=needed)
        self._draw()

    def _draw(self):
        self.canvas.delete("panel")
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        if width <= 2 or height <= 2:
            return
        border = theme.BORDER_HI if self._hover else self._border
        round_rect(self.canvas, 1, 1, width - 2, height - 2, self._radius,
                   self._fill, border, 1, tags="panel")
        self.canvas.tag_lower("panel")


class SectionTitle(tk.Label):
    def __init__(self, master, text, **kw):
        super().__init__(master, text=text.upper(), bg=master["bg"],
                         fg=theme.TEXT_MUTED, font=theme.f(theme.S8, "bold"),
                         anchor="w", **kw)


class Divider(tk.Frame):
    def __init__(self, master, bg=None, colour=None, pad=0):
        bg = bg or master["bg"]
        super().__init__(master, bg=bg)
        tk.Frame(self, bg=colour or theme.HAIRLINE, height=1).pack(fill="x", pady=pad)


class EmptyState(tk.Frame):
    def __init__(self, master, headline, hint, bg=None):
        bg = bg or master["bg"]
        super().__init__(master, bg=bg)
        holder = tk.Canvas(self, width=52, height=52, bg=bg,
                           highlightthickness=0, bd=0)
        holder.pack(pady=(0, 12))
        branding.draw(holder, 26, 26, 52)
        tk.Label(self, text=headline, bg=bg, fg=theme.TEXT,
                 font=theme.f(theme.S13, "bold")).pack()
        self.hint = tk.Label(self, text=hint, bg=bg, fg=theme.TEXT_FAINT,
                             font=theme.f(theme.S9), justify="center", wraplength=380)
        self.hint.pack(pady=(5, 0))


class ToggleSwitch(tk.Canvas):
    def __init__(self, master, variable, width=42, height=22, command=None, bg=None):
        bg = bg or master["bg"]
        super().__init__(master, width=width, height=height, bg=bg,
                         highlightthickness=0, bd=0, cursor="hand2")
        self.var = variable
        self.command = command
        self._width = width
        self._height = height
        self._hover = False
        self.bind("<Button-1>", self._toggle)
        self.bind("<Enter>", lambda e: self._set_hover(True))
        self.bind("<Leave>", lambda e: self._set_hover(False))
        try:
            self.var.trace_add("write", lambda *_: self._draw())
        except AttributeError:
            self.var.trace("w", lambda *_: self._draw())
        self._draw()

    def _set_hover(self, value):
        self._hover = value
        self._draw()

    def _toggle(self, _event=None):
        self.var.set(not self.var.get())
        if self.command:
            self.command()

    def _draw(self):
        self.delete("all")
        on = bool(self.var.get())
        radius = self._height / 2.0
        if on:
            track = theme.ACCENT_HOVER if self._hover else theme.ACCENT
        else:
            track = theme.BORDER_HI if self._hover else theme.SURFACE_ACTIVE
        self.create_oval(0, 0, self._height, self._height, fill=track, outline=track)
        self.create_oval(self._width - self._height, 0, self._width, self._height,
                         fill=track, outline=track)
        self.create_rectangle(radius, 0, self._width - radius, self._height,
                              fill=track, outline=track)
        knob = radius - 3
        cx = self._width - radius if on else radius
        self.create_oval(cx - knob, radius - knob, cx + knob, radius + knob,
                         fill="#ffffff", outline="#ffffff")


class StatTile(tk.Frame):
    def __init__(self, master, label, value="--", accent=None, bg=None):
        bg = bg or theme.SURFACE
        super().__init__(master, bg=bg)
        self._accent = accent or theme.TEXT
        tk.Label(self, text=label.upper(), bg=bg, fg=theme.TEXT_FAINT,
                 font=theme.f(theme.S8, "bold"), anchor="w").pack(fill="x")
        self.value = tk.Label(self, text=value, bg=bg, fg=self._accent,
                              font=theme.f(theme.S15, "bold"), anchor="w")
        self.value.pack(fill="x", pady=(2, 0))

    def set(self, text, colour=None):
        try:
            self.value.configure(text=text, fg=colour or self._accent)
        except tk.TclError:
            pass


class NavItem(tk.Canvas):
    HEIGHT = 42

    def __init__(self, master, label, icon, command, bg=None):
        bg = bg or theme.BG_ALT
        super().__init__(master, height=self.HEIGHT, bg=bg,
                         highlightthickness=0, bd=0, cursor="hand2")
        self.command = command
        self.icon_name = icon
        self._base = bg
        self._active = False
        self._hover = False
        self._badge = 0
        self._label = label

        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Button-1>", lambda e: self.command())
        self.bind("<Enter>", lambda e: self._set_hover(True))
        self.bind("<Leave>", lambda e: self._set_hover(False))
        self._draw()

    def _set_hover(self, value):
        self._hover = value
        self._draw()

    def set_badge(self, count):
        self._badge = max(0, int(count))
        self._draw()

    def _draw(self):
        self.delete("all")
        width = self.winfo_width()
        if width < 20:
            return

        if self._active:
            round_rect(self, 8, 4, width - 8, self.HEIGHT - 4, theme.RADIUS_SM,
                       theme.ACCENT_DIM, theme.ACCENT, 1)
        elif self._hover:
            round_rect(self, 8, 4, width - 8, self.HEIGHT - 4, theme.RADIUS_SM,
                       theme.SURFACE_HI, "")

        colour = theme.ACCENT if self._active else (
            theme.TEXT if self._hover else theme.TEXT_DIM)
        draw = ICONS.get(self.icon_name)
        if draw:
            draw(self, 26, self.HEIGHT / 2, 16, colour, 1.8)

        self.create_text(48, self.HEIGHT / 2, text=self._label, fill=colour,
                         font=theme.f(theme.S10, "bold" if self._active else "normal"),
                         anchor="w")

        if self._badge:
            text = str(self._badge) if self._badge < 10 else "9+"
            cx = width - 24
            self.create_oval(cx - 9, self.HEIGHT / 2 - 9, cx + 9, self.HEIGHT / 2 + 9,
                             fill=theme.RED_DIM, outline=theme.RED, width=1)
            self.create_text(cx, self.HEIGHT / 2, text=text, fill=theme.RED,
                             font=theme.f(theme.S8, "bold"))

    def set_active(self, active):
        self._active = active
        self._draw()


class FlatButton(tk.Label):
    _VARIANTS = {
        "normal": (theme.SURFACE_HI, theme.TEXT, theme.SURFACE_ACTIVE),
        "accent": (theme.ACCENT, "#ffffff", theme.ACCENT_HOVER),
        "ghost": (None, theme.TEXT_DIM, theme.SURFACE_HI),
        "danger": (theme.RED_DIM, theme.RED, theme.RED_SOFT),
        "violet": (theme.VIOLET_DIM, theme.VIOLET, theme.VIOLET_SOFT),
    }

    def __init__(self, master, text, command, kind="normal", bg=None, width=None):
        bg = bg or theme.SURFACE
        base, fg, hover = self._VARIANTS.get(kind, self._VARIANTS["normal"])
        base = base or bg
        super().__init__(master, text=text, bg=base, fg=fg,
                         font=theme.f(theme.S9, "bold"), padx=13, pady=6,
                         cursor="hand2", width=width)
        self._base_bg = base
        self._hover_bg = hover
        self._fg = fg
        self.command = command
        self._enabled = True
        self.bind("<Button-1>", self._press)
        self.bind("<ButtonRelease-1>", self._release)
        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)

    def _enter(self, _e):
        if self._enabled:
            self.configure(bg=self._hover_bg)

    def _leave(self, _e):
        if self._enabled:
            self.configure(bg=self._base_bg, fg=self._fg)

    def _press(self, _e):
        if self._enabled:
            self.configure(bg=theme.darken(self._hover_bg, 0.10))

    def _release(self, _e):
        if not self._enabled:
            return
        self._enter(None)
        self.command()

    def set_enabled(self, value):
        self._enabled = bool(value)
        self.configure(cursor="hand2" if value else "arrow",
                       fg=self._fg if value else theme.TEXT_FAINT)


class Chip(tk.Label):
    def __init__(self, master, text, command, bg=None):
        bg = bg or theme.BG
        super().__init__(master, text=text, bg=theme.SURFACE_HI, fg=theme.TEXT_MUTED,
                         font=theme.f(theme.S8, "bold"), padx=11, pady=5,
                         cursor="hand2")
        self.command = command
        self._bg = bg
        self._selected = False
        self.bind("<Button-1>", lambda e: self.command())
        self.bind("<Enter>", lambda e: self._hover(True))
        self.bind("<Leave>", lambda e: self._hover(False))

    def _hover(self, on):
        if not self._selected:
            self.configure(bg=theme.SURFACE_ACTIVE if on else theme.SURFACE_HI,
                           fg=theme.TEXT_DIM if on else theme.TEXT_MUTED)

    def set_selected(self, value):
        self._selected = value
        self.configure(bg=theme.ACCENT if value else theme.SURFACE_HI,
                       fg="#ffffff" if value else theme.TEXT_MUTED)


class SearchField(tk.Frame):
    def __init__(self, master, variable, placeholder="Search", bg=None):
        bg = bg or theme.BG
        super().__init__(master, bg=bg)
        self.var = variable
        self._placeholder = placeholder
        self._empty = True

        box = tk.Frame(self, bg=theme.SURFACE, highlightthickness=1,
                       highlightbackground=theme.BORDER, highlightcolor=theme.ACCENT)
        box.pack(fill="x")

        self.glyph = tk.Canvas(box, width=32, height=34, bg=theme.SURFACE,
                               highlightthickness=0, bd=0)
        self.glyph.pack(side="left")
        ICONS["search"](self.glyph, 16, 17, 14, theme.TEXT_FAINT, 1.7)

        self.entry = tk.Entry(box, textvariable=variable, bg=theme.SURFACE,
                              fg=theme.TEXT, insertbackground=theme.TEXT,
                              relief="flat", font=theme.f(theme.S10), bd=0,
                              highlightthickness=0)
        self.entry.pack(side="left", fill="x", expand=True, ipady=7, padx=(0, 10))
        self.entry.bind("<FocusIn>", lambda e: box.configure(
            highlightbackground=theme.ACCENT))
        self.entry.bind("<FocusOut>", lambda e: box.configure(
            highlightbackground=theme.BORDER))

        self.hint = tk.Label(box, text=placeholder, bg=theme.SURFACE,
                             fg=theme.TEXT_FAINT, font=theme.f(theme.S10))
        self.hint.place(x=34, rely=0.5, anchor="w")
        self.hint.bind("<Button-1>", lambda e: self.entry.focus_set())

        try:
            variable.trace_add("write", lambda *_: self._sync())
        except AttributeError:
            variable.trace("w", lambda *_: self._sync())

    def _sync(self):
        empty = not self.var.get()
        if empty and not self._empty:
            self.hint.place(x=34, rely=0.5, anchor="w")
        elif not empty and self._empty:
            self.hint.place_forget()
        self._empty = empty


class ScrollFrame(tk.Frame):
    def __init__(self, master, bg=None):
        bg = bg or theme.BG
        super().__init__(master, bg=bg)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.scrollbar = tk.Scrollbar(self, orient="vertical",
                                      command=self.canvas.yview,
                                      bg=theme.SURFACE_HI, troughcolor=bg,
                                      activebackground=theme.BORDER_HI,
                                      relief="flat", bd=0, width=8)
        self.inner = tk.Frame(self.canvas, bg=bg)
        self._win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self._on_scroll)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y", padx=(6, 0))
        self.inner.bind("<Configure>", self._on_inner)
        self.canvas.bind("<Configure>", self._on_canvas)
        self.canvas.bind("<Enter>", lambda e: self.canvas.bind_all(
            "<MouseWheel>", self._wheel))
        self.canvas.bind("<Leave>", lambda e: self.canvas.unbind_all("<MouseWheel>"))

    def _on_scroll(self, first, last):
        if float(first) <= 0.0 and float(last) >= 1.0:
            self.scrollbar.pack_forget()
        elif not self.scrollbar.winfo_ismapped():
            self.scrollbar.pack(side="right", fill="y", padx=(6, 0))
        self.scrollbar.set(first, last)

    def _on_inner(self, _event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas(self, event):
        self.canvas.itemconfigure(self._win, width=event.width)

    def _wheel(self, event):
        self.canvas.yview_scroll(int(-event.delta / 120), "units")


class Sparkline(tk.Canvas):
    def __init__(self, master, height=58, colour=theme.ACCENT, bg=None, samples=70):
        bg = bg or theme.SURFACE
        super().__init__(master, height=height, bg=bg, highlightthickness=0, bd=0)
        self.colour = colour
        self._bg = bg
        self.samples = [0.0] * samples
        self.peak = 1024.0
        self.bind("<Configure>", lambda e: self.redraw())

    def push(self, value):
        self.samples.append(max(0.0, value))
        self.samples.pop(0)
        self.peak = max(max(self.samples), 1024.0)
        self.redraw()

    def redraw(self):
        self.delete("all")
        width = self.winfo_width()
        height = self.winfo_height()
        if width < 8 or height < 8:
            return

        for row in (0.25, 0.5, 0.75):
            y = height * row
            self.create_line(0, y, width, y, fill=theme.HAIRLINE, width=1)

        step = width / float(len(self.samples) - 1)
        points = []
        for index, value in enumerate(self.samples):
            x = index * step
            y = height - 2 - (value / self.peak) * (height - 8)
            points.append((x, y))
        flat = [coord for point in points for coord in point]

        self.create_polygon(flat + [width, height, 0, height],
                            fill=theme.fade(self.colour, self._bg, 0.16),
                            outline="", smooth=True)
        self.create_line(flat, fill=theme.fade(self.colour, self._bg, 0.42),
                         width=4, smooth=True)
        self.create_line(flat, fill=self.colour, width=2, smooth=True)

        last = points[-1]
        self.create_oval(last[0] - 4.5, last[1] - 4.5, last[0] + 4.5, last[1] + 4.5,
                         fill=theme.fade(self.colour, self._bg, 0.30), outline="")
        self.create_oval(last[0] - 2.2, last[1] - 2.2, last[0] + 2.2, last[1] + 2.2,
                         fill=self.colour, outline=self.colour)


class ScoreGauge(tk.Canvas):
    def __init__(self, master, size=150, bg=None):
        bg = bg or theme.BG
        super().__init__(master, width=size, height=size, bg=bg,
                         highlightthickness=0, bd=0)
        self.size = size
        self._bg = bg
        self.value = 0.0
        self.target = 0.0
        self.grade = "-"
        self._job = None

        self._disc = self.create_oval(0, 0, 0, 0, outline=theme.SURFACE_HI, width=1)
        self._track = self.create_arc(0, 0, 0, 0, start=90, extent=-360,
                                      style="arc", outline=theme.SURFACE_HI, width=8)
        self._sweep = self.create_arc(0, 0, 0, 0, start=90, extent=0,
                                      style="arc", outline=theme.ACCENT, width=8)
        self._value = self.create_text(0, 0, text="--", font=theme.f(28, "bold"),
                                       fill=theme.TEXT)
        self._grade = self.create_text(0, 0, text="", font=theme.f(theme.S9, "bold"),
                                       fill=theme.TEXT_FAINT)
        self._layout()

    def _layout(self):
        pad = 14
        self.coords(self._disc, pad - 5, pad - 5, self.size - pad + 5, self.size - pad + 5)
        for item in (self._track, self._sweep):
            self.coords(item, pad, pad, self.size - pad, self.size - pad)
        self.coords(self._value, self.size / 2, self.size / 2 - 5)
        self.coords(self._grade, self.size / 2, self.size / 2 + 23)

    def set_score(self, score, grade):
        self.target = max(0.0, min(100.0, float(score)))
        self.grade = grade
        if self._job is None:
            self._step()

    def _step(self):
        try:
            delta = self.target - self.value
            if abs(delta) < 0.6:
                self.value = self.target
                self._job = None
            else:
                self.value += delta * theme.DRAG_EASE
                self._job = self.after(20, self._step)
            self._render()
        except tk.TclError:
            self._job = None

    def _render(self):
        score = int(round(self.value))
        colour = (theme.GREEN if score >= 85 else theme.ACCENT if score >= 70
                  else theme.AMBER if score >= 55 else theme.RED)
        self.itemconfigure(self._sweep, extent=-3.6 * self.value, outline=colour)
        self.itemconfigure(self._value, text=str(score), fill=colour)
        self.itemconfigure(self._grade, text=self.grade, fill=colour)


class ConnectButton(tk.Canvas):
    """Radial power control. Glyph is a proper power symbol, label sits clear."""

    def __init__(self, master, size=200, command=None, bg=None):
        bg = bg or theme.BG
        super().__init__(master, width=size, height=size, bg=bg,
                         highlightthickness=0, bd=0, cursor="hand2")
        self.size = size
        self._bg = bg
        self.command = command
        self.state = "idle"
        self.hover = False
        self._spin = 0
        self._pulse = 0.0
        self._pulse_dir = 1
        self._job = None

        self._outer = size * 0.455
        self._inner = size * 0.375

        self._glow3 = self.create_oval(0, 0, 0, 0, outline="", fill=bg)
        self._glow2 = self.create_oval(0, 0, 0, 0, outline="", fill=bg)
        self._glow1 = self.create_oval(0, 0, 0, 0, outline="", fill=bg)
        self._halo = self.create_oval(0, 0, 0, 0, outline=theme.BORDER, width=1)
        self._arc1 = self.create_arc(0, 0, 0, 0, start=0, extent=110,
                                     style="arc", outline=theme.ACCENT, width=3,
                                     state="hidden")
        self._arc2 = self.create_arc(0, 0, 0, 0, start=180, extent=70,
                                     style="arc", outline=theme.ACCENT_DIM, width=3,
                                     state="hidden")
        self._disc = self.create_oval(0, 0, 0, 0, outline="")
        self._rim = self.create_oval(0, 0, 0, 0, outline="", width=1)
        self._glyph_arc = self.create_arc(0, 0, 0, 0, start=55, extent=250,
                                          style="arc", width=4, outline=theme.TEXT)
        self._glyph_line = self.create_line(0, 0, 0, 0, width=4, fill=theme.TEXT)
        self._label = self.create_text(0, 0, text="CONNECT",
                                       font=theme.f(theme.S9, "bold"), fill=theme.TEXT)

        self.bind("<Button-1>", lambda e: self.command() if self.command else None)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self._layout()
        self.redraw()

    def _layout(self):
        size = self.size
        cx = cy = size / 2.0
        for scale, item in ((self._outer * 1.17, self._glow3),
                            (self._outer * 1.09, self._glow2),
                            (self._outer * 1.02, self._glow1)):
            self.coords(item, cx - scale, cy - scale, cx + scale, cy + scale)
        for item in (self._halo, self._arc1, self._arc2):
            self.coords(item, cx - self._outer, cy - self._outer,
                        cx + self._outer, cy + self._outer)
        self.coords(self._disc, cx - self._inner, cy - self._inner,
                    cx + self._inner, cy + self._inner)
        inset = self._inner * 0.90
        self.coords(self._rim, cx - inset, cy - inset, cx + inset, cy + inset)

        r = size * 0.115
        gy = cy - size * 0.055
        self.coords(self._glyph_arc, cx - r, gy - r, cx + r, gy + r)
        self.coords(self._glyph_line, cx, gy - r * 1.45, cx, gy - r * 0.10)
        self.coords(self._label, cx, cy + size * 0.245)

    def _on_enter(self, _e):
        self.hover = True
        self.redraw()

    def _on_leave(self, _e):
        self.hover = False
        self.redraw()

    def set_state(self, state):
        if state == self.state:
            return
        self.state = state
        if self._job is None:
            self._tick()
        self.redraw()

    def _tick(self):
        try:
            if self.state == "connecting":
                self._spin = (self._spin + 6) % 360
                self.itemconfigure(self._arc1, start=self._spin)
                self.itemconfigure(self._arc2, start=(self._spin + 180) % 360)
            elif self.state == "connected":
                self._pulse += 0.05 * self._pulse_dir
                if self._pulse >= 1.0 or self._pulse <= 0.0:
                    self._pulse_dir = -self._pulse_dir
                self._pulse = max(0.0, min(1.0, self._pulse))
                self._paint_glow()
            self._job = self.after(theme.TICK_MS, self._tick)
        except tk.TclError:
            self._job = None

    def _palette(self):
        if self.state == "connected":
            return theme.GREEN, theme.GREEN_DIM, theme.GREEN, "DISCONNECT"
        if self.state == "connecting":
            return theme.ACCENT, theme.ACCENT_DIM, theme.ACCENT, "CANCEL"
        if self.state == "failed":
            return theme.RED, theme.RED_DIM, theme.RED, "RETRY"
        if self.hover:
            return theme.ACCENT, theme.ACCENT_DIM, theme.ACCENT, "CONNECT"
        return theme.BORDER_HI, theme.SURFACE_HI, theme.TEXT, "CONNECT"

    def _paint_glow(self):
        ring, _fill, _glyph, _label = self._palette()
        base = 0.10 if self.state == "connected" else 0.0
        strength = base + self._pulse * 0.12
        for index, item in enumerate((self._glow1, self._glow2, self._glow3)):
            amount = strength * (1.0 - index * 0.30)
            self.itemconfigure(item, fill=theme.fade(ring, self._bg, amount))

    def redraw(self):
        ring, fill, glyph, label = self._palette()
        spinning = self.state == "connecting"
        self.itemconfigure(self._halo, outline=ring, width=2 if spinning else 1)
        self.itemconfigure(self._arc1, state="normal" if spinning else "hidden",
                           outline=ring)
        self.itemconfigure(self._arc2, state="normal" if spinning else "hidden",
                           outline=ring)
        self.itemconfigure(self._disc, fill=fill, outline="")
        self.itemconfigure(self._rim, outline=theme.fade(ring, fill, 0.40))
        self.itemconfigure(self._glyph_arc, outline=glyph)
        self.itemconfigure(self._glyph_line, fill=glyph)
        self.itemconfigure(self._label, text=label, fill=glyph)
        self._paint_glow()


class FindingRow(tk.Canvas):
    HEIGHT = 46

    def __init__(self, master, finding, on_toggle):
        self.finding = finding
        self._expanded = False
        self._hover = False
        self._height = self.HEIGHT
        super().__init__(master, height=self._height, bg=theme.BG,
                         highlightthickness=0, bd=0, cursor="hand2")
        self.on_toggle = on_toggle
        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Button-1>", self._click)
        self.bind("<Enter>", lambda e: self._set_hover(True))
        self.bind("<Leave>", lambda e: self._set_hover(False))

    def _set_hover(self, value):
        self._hover = value
        self._draw()

    def _click(self, _event):
        self._expanded = not self._expanded
        self.on_toggle(self)
        self._draw()

    @property
    def expanded(self):
        return self._expanded

    def _draw(self):
        self.delete("all")
        width = self.winfo_width()
        if width < 20:
            return
        finding = self.finding
        colour = theme.severity_colour(finding.severity.value)

        fill = theme.SURFACE_HI if self._hover else theme.SURFACE
        round_rect(self, 1, 2, width - 2, self._height - 2, theme.RADIUS_SM,
                   fill, theme.BORDER if not self._hover else theme.BORDER_HI, 1)

        round_rect(self, 1, 9, 4, self._height - 9, 2, colour, "")

        badge = finding.severity.value.upper()
        if finding.status.value == "pass":
            badge, colour = "PASS", theme.GREEN
        elif finding.status.value == "info":
            badge, colour = "INFO", theme.TEXT_FAINT

        self.create_text(18, self._height / 2, text=badge, fill=colour,
                         font=theme.f(theme.S8, "bold"), anchor="w")
        self.create_text(84, 15, text=finding.title, fill=theme.TEXT,
                         font=theme.f(theme.S10, "bold"), anchor="w")
        self.create_text(84, 30, text=finding.summary[:110], fill=theme.TEXT_FAINT,
                         font=theme.f(theme.S8), anchor="w")
        self.create_text(width - 16, self._height / 2,
                         text="v" if self._expanded else ">",
                         fill=theme.TEXT_FAINT, font=theme.m(theme.S9), anchor="e")

    def set_expanded(self, value):
        self._expanded = value
        self._draw()