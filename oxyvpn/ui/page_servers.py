"""Server browser page."""

from __future__ import annotations

import math
import threading
import tkinter as tk

from ..netinfo import probe_latency
from . import theme
from .widgets import (Chip, EmptyState, Eyebrow, FlatButton, ScrollFrame,
                      SearchField, draw_flag, round_rect)

SORTS = [("Name", "name"), ("Latency", "latency"), ("Favorites", "favorites")]


class ServerRow(tk.Canvas):
    HEIGHT = 56
    _latency = -2

    def __init__(self, master, profile, on_connect, on_select, on_star):
        super().__init__(master, height=self.HEIGHT, bg=theme.BG,
                         highlightthickness=0, bd=0, cursor="hand2")
        self.profile = profile
        self.on_connect = on_connect
        self.on_select = on_select
        self.on_star = on_star
        self._hover = False
        self._selected = False
        self._favorite = False

        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Button-1>", self._click)
        self.bind("<Double-Button-1>", lambda e: self.on_connect(self.profile))
        self.bind("<Enter>", lambda e: self._set_hover(True))
        self.bind("<Leave>", lambda e: self._set_hover(False))

    def _click(self, event):
        if event.x < 30:
            self.on_star(self.profile)
        else:
            self.on_select(self.profile)

    def _set_hover(self, value):
        self._hover = value
        self._draw()

    def set_selected(self, value):
        self._selected = value
        self._draw()

    def set_favorite(self, value):
        self._favorite = value
        self._draw()

    def set_latency(self, ms):
        self._latency = ms
        self._draw()

    def _star(self, cx, cy, radius, colour, filled):
        points = []
        for index in range(10):
            angle = -math.pi / 2 + index * math.pi / 5
            span = radius if index % 2 == 0 else radius * 0.44
            points += [cx + math.cos(angle) * span, cy + math.sin(angle) * span]
        self.create_polygon(points, fill=colour if filled else "",
                            outline=colour, width=1)

    def _draw(self):
        self.delete("all")
        width = self.winfo_width()
        if width < 20:
            return

        if self._selected:
            fill, border = theme.ACCENT_DIM, theme.ACCENT
        elif self._hover:
            fill, border = theme.SURFACE_HI, theme.BORDER_HI
        else:
            fill, border = theme.SURFACE, theme.BORDER

        round_rect(self, 1, 2, width - 2, self.HEIGHT - 2, theme.RADIUS, fill, border, 1)

        star_colour = theme.AMBER if self._favorite else theme.TEXT_FAINT
        self._star(16, self.HEIGHT / 2, 6, star_colour, self._favorite)

        draw_flag(self, 47, self.HEIGHT / 2, 34, 22,
                  (self.profile.country_code or "").lower())

        self.create_text(77, self.HEIGHT / 2 - 9, text=self.profile.title,
                         fill=theme.TEXT, font=theme.f(theme.S10, "bold"), anchor="w")

        host, _, proto = self.profile.subtitle.rpartition(" ")
        self.create_text(77, self.HEIGHT / 2 + 9, text=host,
                         fill=theme.TEXT_FAINT, font=theme.m(theme.S8), anchor="w")

        if self.profile.issues:
            badge = "%d!" % len(self.profile.issues)
            round_rect(self, width - 190, self.HEIGHT / 2 + 2, width - 162,
                       self.HEIGHT / 2 + 16, 3, theme.AMBER_DIM, "")
            self.create_text(width - 176, self.HEIGHT / 2 + 9, text=badge,
                             fill=theme.AMBER, font=theme.f(7, "bold"))

        pill = theme.ACCENT_DIM if proto == "UDP" else theme.VIOLET_DIM
        text_colour = theme.ACCENT if proto == "UDP" else theme.VIOLET
        round_rect(self, width - 156, self.HEIGHT / 2 + 2, width - 122,
                   self.HEIGHT / 2 + 16, 3, pill, "")
        self.create_text(width - 139, self.HEIGHT / 2 + 9, text=proto,
                         fill=text_colour, font=theme.f(7, "bold"))

        if self._latency == -2:
            text, colour = "--", theme.TEXT_FAINT
        elif self._latency < 0:
            text, colour = "timeout", theme.TEXT_FAINT
        else:
            colour = theme.GREEN if self._latency < 90 else \
                theme.AMBER if self._latency < 200 else theme.RED
            text = "%d ms" % int(self._latency)
            bar = 28
            filled = max(3, min(bar, int(bar * (1.0 - min(self._latency, 400) / 400.0))))
            round_rect(self, width - 112, self.HEIGHT / 2 + 10, width - 112 + bar,
                       self.HEIGHT / 2 + 13, 2, theme.SURFACE_ACTIVE, "")
            round_rect(self, width - 112, self.HEIGHT / 2 + 10, width - 112 + filled,
                       self.HEIGHT / 2 + 13, 2, colour, "")

        self.create_text(width - 20, self.HEIGHT / 2 - 7, text=text, fill=colour,
                         font=theme.m(theme.S8), anchor="e")

        if self.profile.is_free:
            self.create_text(width - 20, self.HEIGHT / 2 + 12, text="FREE",
                             fill=theme.GREEN, font=theme.f(theme.S8, "bold"),
                             anchor="e")


class ServersPage(tk.Frame):
    def __init__(self, master, app):
        super().__init__(master, bg=theme.BG)
        self.app = app
        self.rows = []
        self._latencies = {}
        self._sort = app.store.data.sort_mode

        header = tk.Frame(self, bg=theme.BG)
        header.pack(fill="x", padx=28, pady=(18, 10))
        Eyebrow(header, "Network").pack(fill="x")
        line = tk.Frame(header, bg=theme.BG)
        line.pack(fill="x", pady=(2, 0))
        tk.Label(line, text="Servers", bg=theme.BG, fg=theme.TEXT,
                 font=theme.f(theme.S28, "bold")).pack(side="left")
        FlatButton(line, "Rescan", self.app.reload_profiles,
                   kind="ghost").pack(side="right", pady=(6, 0))
        FlatButton(line, "Add profiles", self.app.import_profiles,
                   kind="accent").pack(side="right", padx=8, pady=(6, 0))
        FlatButton(line, "Measure latency", self.measure_latency,
                   kind="ghost").pack(side="right", padx=(0, 8), pady=(6, 0))
        self.count_label = tk.Label(line, text="", bg=theme.BG, fg=theme.TEXT_FAINT,
                                    font=theme.m(theme.S8))
        self.count_label.pack(side="right", padx=(0, 14), pady=(8, 0))

        self.query = tk.StringVar()
        try:
            self.query.trace_add("write", lambda *_: self._filter())
        except AttributeError:
            self.query.trace("w", lambda *_: self._filter())
        SearchField(self, self.query, "Filter by country, city or host").pack(
            fill="x", padx=28)

        tools = tk.Frame(self, bg=theme.BG)
        tools.pack(fill="x", padx=28, pady=(10, 0))
        tk.Label(tools, text="SORT", bg=theme.BG, fg=theme.TEXT_FAINT,
                 font=theme.f(theme.S8, "bold")).pack(side="left", padx=(0, 8))
        self.sort_chips = {}
        for label, mode in SORTS:
            chip = Chip(tools, label, lambda m=mode: self._set_sort(m))
            chip.pack(side="left", padx=(0, 6))
            self.sort_chips[mode] = chip
        self.sort_chips.get(self._sort, self.sort_chips["name"]).set_selected(True)

        self.scroll = ScrollFrame(self, bg=theme.BG)
        self.scroll.pack(fill="both", expand=True, padx=28, pady=(12, 20))

        self.empty = EmptyState(self.scroll.inner, "No profiles found",
                                "Press Add profiles, or drop .ovpn files in the "
                                "folder below.")

    def _favorites(self):
        return set(self.app.store.data.favorites or [])

    def _set_sort(self, mode):
        self._sort = mode
        self.app.store.update(sort_mode=mode)
        for key, chip in self.sort_chips.items():
            chip.set_selected(key == mode)
        self._order()

    def _order(self):
        favorites = self._favorites()
        if self._sort == "latency":
            self.rows.sort(key=lambda r: self._latencies.get(r.profile.key, 99999))
        elif self._sort == "favorites":
            self.rows.sort(key=lambda r: (0 if r.profile.key in favorites else 1,
                                          r.profile.title.lower()))
        else:
            self.rows.sort(key=lambda r: r.profile.title.lower())
        for row in self.rows:
            row.pack_forget()
        for row in self.rows:
            row.pack(fill="x", pady=2)
        self._filter()

    def refresh(self):
        for row in self.rows:
            row.destroy()
        self.rows = []

        if not self.app.profiles:
            self.count_label.configure(text="0 profiles")
            self.empty.hint.configure(text="Profiles folder:\n"
                                           + self.app.profiles_dir_text())
            self.empty.pack(pady=40)
            return

        self.empty.pack_forget()
        favorites = self._favorites()
        for profile in self.app.profiles:
            row = ServerRow(self.scroll.inner, profile,
                            on_connect=self.app.connect_to,
                            on_select=self.app.select_profile,
                            on_star=self.app.toggle_favorite)
            row.set_selected(profile is self.app.selected)
            row.set_favorite(profile.key in favorites)
            self.rows.append(row)
        self._order()

    def _filter(self):
        needle = self.query.get().strip().lower()
        visible = 0
        for row in self.rows:
            haystack = (row.profile.title + " " + row.profile.subtitle).lower()
            if not needle or needle in haystack:
                row.pack(fill="x", pady=2)
                visible += 1
            else:
                row.pack_forget()
        self.count_label.configure(text="%d of %d" % (visible, len(self.rows))
                                   if needle else "%d profiles" % len(self.rows))

    def measure_latency(self):
        rows = list(self.rows)

        def worker():
            for row in rows:
                ms = probe_latency(row.profile.host, row.profile.port,
                                   row.profile.proto)
                self.app.post(lambda r=row, m=ms: self._set_latency(r, m))

        threading.Thread(target=worker, daemon=True).start()

    def _set_latency(self, row, ms):
        self._latencies[row.profile.key] = ms if ms > 0 else 99998
        row.set_latency(ms)
        if self._sort == "latency":
            self._order()