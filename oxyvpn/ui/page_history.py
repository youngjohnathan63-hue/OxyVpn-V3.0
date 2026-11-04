"""Session history page with a detail inspector."""

from __future__ import annotations

import time
import tkinter as tk
from tkinter import filedialog

from ..vpn import history
from . import theme
from .widgets import EmptyState, Eyebrow, FlatButton, ScrollFrame, round_rect


def _duration(seconds):
    seconds = int(max(0, seconds))
    if seconds < 60:
        return "%ds" % seconds
    if seconds < 3600:
        return "%dm %02ds" % (seconds // 60, seconds % 60)
    return "%dh %02dm" % (seconds // 3600, (seconds % 3600) // 60)


def _size(total):
    total = max(0, int(total))
    if total < 1024:
        return "%d B" % total
    if total < 1024 * 1024:
        return "%.1f KB" % (total / 1024.0)
    if total < 1024 * 1024 * 1024:
        return "%.1f MB" % (total / (1024.0 * 1024.0))
    return "%.2f GB" % (total / (1024.0 * 1024.0 * 1024.0))


def _stamp(value, fmt="%Y-%m-%d %H:%M"):
    return time.strftime(fmt, time.localtime(value)) if value else "--"


def _day_label(value):
    if not value:
        return "Unknown date"
    today = time.strftime("%Y-%m-%d")
    yesterday = time.strftime("%Y-%m-%d", time.localtime(time.time() - 86400))
    day = time.strftime("%Y-%m-%d", time.localtime(value))
    if day == today:
        return "Today"
    if day == yesterday:
        return "Yesterday"
    return time.strftime("%A %d %B %Y", time.localtime(value))


class TotalTile(tk.Canvas):
    HEIGHT = 62

    def __init__(self, master, label, accent):
        super().__init__(master, height=self.HEIGHT, bg=theme.BG,
                         highlightthickness=0, bd=0)
        self._label = label
        self._accent = accent
        self._value = "0"
        self._colour = accent
        self.bind("<Configure>", lambda e: self.redraw())

    def set(self, value, colour=None):
        self._value = value
        self._colour = colour or self._accent
        self.redraw()

    def redraw(self):
        self.delete("all")
        width = self.winfo_width()
        if width < 20:
            return
        round_rect(self, 1, 1, width - 2, self.HEIGHT - 2, theme.RADIUS,
                   theme.SURFACE, theme.BORDER, 1)
        self.create_text(14, 17, text=self._label.upper(), fill=theme.TEXT_FAINT,
                         font=theme.f(theme.S8, "bold"), anchor="w")
        self.create_text(14, 39, text=self._value, fill=self._colour,
                         font=theme.f(theme.S18, "bold"), anchor="w")


class DayHeader(tk.Canvas):
    HEIGHT = 30

    def __init__(self, master, text):
        super().__init__(master, height=self.HEIGHT, bg=theme.BG,
                         highlightthickness=0, bd=0)
        self._text = text
        self.bind("<Configure>", lambda e: self.redraw())

    def redraw(self):
        self.delete("all")
        width = self.winfo_width()
        if width < 40:
            return
        self.create_text(2, self.HEIGHT / 2, text=self._text.upper(),
                         fill=theme.TEXT_MUTED, font=theme.f(theme.S8, "bold"),
                         anchor="w")
        self.create_line(90, self.HEIGHT / 2, width, self.HEIGHT / 2,
                         fill=theme.HAIRLINE, width=1)


class HistoryRow(tk.Canvas):
    HEIGHT = 56

    def __init__(self, master, entry, on_open):
        super().__init__(master, height=self.HEIGHT, bg=theme.BG,
                         highlightthickness=0, bd=0, cursor="hand2")
        self.entry = entry
        self.on_open = on_open
        self._hover = False
        self._selected = False
        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Button-1>", lambda e: self.on_open(self))
        self.bind("<Double-Button-1>", lambda e: self.on_open(self))
        self.bind("<Enter>", lambda e: self._set(True))
        self.bind("<Leave>", lambda e: self._set(False))

    def _set(self, value):
        self._hover = value
        self._draw()

    def set_selected(self, value):
        self._selected = value
        self._draw()

    def _draw(self):
        self.delete("all")
        width = self.winfo_width()
        if width < 20:
            return

        outcome = self.entry.get("outcome") or "ok"
        colour = theme.GREEN if outcome == "ok" else theme.RED

        if self._selected:
            fill, border = theme.ACCENT_DIM, theme.ACCENT
        elif self._hover:
            fill, border = theme.SURFACE_HI, theme.BORDER_HI
        else:
            fill, border = theme.SURFACE, theme.BORDER

        round_rect(self, 1, 2, width - 2, self.HEIGHT - 2, theme.RADIUS_SM,
                   fill, border, 1)
        round_rect(self, 1, 10, 4, self.HEIGHT - 10, 2, colour, "")

        server = self.entry.get("server") or "unknown"
        self.create_text(18, self.HEIGHT / 2 - 8, text=server[:42],
                         fill=theme.TEXT, font=theme.f(theme.S10, "bold"), anchor="w")

        host = self.entry.get("host") or ""
        proto = (self.entry.get("proto") or "").upper()
        port = self.entry.get("port") or ""
        detail = host + (":%s" % port if port else "") + ("  " + proto if proto else "")
        self.create_text(18, self.HEIGHT / 2 + 9, text=detail or "--",
                         fill=theme.TEXT_FAINT, font=theme.m(theme.S8), anchor="w")

        self.create_text(width - 16, self.HEIGHT / 2 - 8,
                         text=_duration(self.entry.get("seconds") or 0),
                         fill=theme.TEXT_DIM, font=theme.m(theme.S8), anchor="e")
        total = int(self.entry.get("down") or 0) + int(self.entry.get("up") or 0)
        self.create_text(width - 16, self.HEIGHT / 2 + 9, text=_size(total),
                         fill=theme.TEXT_FAINT, font=theme.m(theme.S8), anchor="e")


class DetailPanel(tk.Frame):
    WIDTH = 320

    def __init__(self, master, on_close, on_copy):
        super().__init__(master, bg=theme.SURFACE, width=self.WIDTH)
        self.pack_propagate(False)
        self.entry = None

        head = tk.Frame(self, bg=theme.SURFACE)
        head.pack(fill="x", padx=16, pady=(16, 8))
        tk.Label(head, text="SESSION DETAIL", bg=theme.SURFACE, fg=theme.TEXT_FAINT,
                 font=theme.f(theme.S8, "bold"), anchor="w").pack(side="left")
        close = tk.Label(head, text="x", bg=theme.SURFACE, fg=theme.TEXT_FAINT,
                         font=theme.f(theme.S11), cursor="hand2")
        close.pack(side="right")
        close.bind("<Button-1>", lambda e: on_close())

        self.title = tk.Label(self, text="", bg=theme.SURFACE, fg=theme.TEXT,
                              font=theme.f(theme.S13, "bold"), anchor="w",
                              justify="left", wraplength=self.WIDTH - 32)
        self.title.pack(fill="x", padx=16)

        self.badge = tk.Label(self, text="", bg=theme.GREEN_DIM, fg=theme.GREEN,
                              font=theme.f(theme.S8, "bold"), padx=8, pady=2)
        self.badge.pack(anchor="w", padx=16, pady=(8, 12))

        self.rows = {}
        for key, label in (("host", "Server"), ("proto", "Protocol"),
                           ("tunnel", "Tunnel IP"), ("exit", "Exit IP"),
                           ("started", "Started"), ("ended", "Ended"),
                           ("duration", "Duration"), ("data", "Data")):
            row = tk.Frame(self, bg=theme.SURFACE)
            row.pack(fill="x", padx=16, pady=3)
            tk.Label(row, text=label.upper(), bg=theme.SURFACE, fg=theme.TEXT_FAINT,
                     font=theme.f(7, "bold"), anchor="w", width=10).pack(side="left")
            value = tk.Label(row, text="--", bg=theme.SURFACE, fg=theme.TEXT_DIM,
                             font=theme.m(theme.S8), anchor="w", justify="left",
                             wraplength=self.WIDTH - 150)
            value.pack(side="left", fill="x", expand=True)
            self.rows[key] = value

        self.ks = tk.Label(self, text="", bg=theme.SURFACE, fg=theme.TEXT_FAINT,
                           font=theme.f(theme.S8), anchor="w", justify="left",
                           wraplength=self.WIDTH - 32)
        self.ks.pack(fill="x", padx=16, pady=(10, 0))

        self.copy_button = FlatButton(self, "Copy details", on_copy, kind="ghost")
        self.copy_button.pack(fill="x", padx=16, pady=(14, 16), side="bottom")

    def show(self, entry):
        self.entry = entry
        self.title.configure(text=entry.get("server") or "unknown")
        outcome = entry.get("outcome") or "ok"
        if outcome == "ok":
            self.badge.configure(text="CLEAN EXIT", bg=theme.GREEN_DIM, fg=theme.GREEN)
        else:
            self.badge.configure(text="FAILED", bg=theme.RED_DIM, fg=theme.RED)

        host = entry.get("host") or "--"
        port = entry.get("port")
        proto = (entry.get("proto") or "").upper()
        self.rows["host"].configure(text=host + (":%s" % port if port else ""))
        self.rows["proto"].configure(text=proto or "--")
        self.rows["tunnel"].configure(text=entry.get("tunnel_ip") or "--")
        self.rows["exit"].configure(text=entry.get("exit_ip") or "not captured")
        self.rows["started"].configure(text=_stamp(entry.get("started")))
        self.rows["ended"].configure(text=_stamp(entry.get("ended")))
        self.rows["duration"].configure(text=_duration(entry.get("seconds") or 0))
        self.rows["data"].configure(
            text="%s down / %s up" % (_size(entry.get("down") or 0),
                                      _size(entry.get("up") or 0)))
        self.ks.configure(
            text="Kill switch was on during this session." if entry.get("kill_switch")
            else "Kill switch was off during this session.",
            fg=theme.GREEN if entry.get("kill_switch") else theme.AMBER)

    def clear(self):
        self.entry = None


class HistoryPage(tk.Frame):
    def __init__(self, master, app):
        super().__init__(master, bg=theme.BG)
        self.app = app
        self.rows = []
        self._active = None

        header = tk.Frame(self, bg=theme.BG)
        header.pack(fill="x", padx=28, pady=(18, 10))
        Eyebrow(header, "Telemetry").pack(fill="x")
        line = tk.Frame(header, bg=theme.BG)
        line.pack(fill="x", pady=(2, 0))
        tk.Label(line, text="History", bg=theme.BG, fg=theme.TEXT,
                 font=theme.f(theme.S28, "bold")).pack(side="left")
        FlatButton(line, "Export", self._export, kind="ghost").pack(side="right", pady=(6, 0))
        FlatButton(line, "Clear", self._clear, kind="ghost").pack(side="right", padx=8, pady=(6, 0))
        self.count_label = tk.Label(line, text="", bg=theme.BG, fg=theme.TEXT_FAINT,
                                    font=theme.m(theme.S8))
        self.count_label.pack(side="right", padx=(0, 14), pady=(8, 0))

        cards = tk.Frame(self, bg=theme.BG)
        cards.pack(fill="x", padx=28, pady=(0, 12))
        for column in range(4):
            cards.columnconfigure(column, weight=1, uniform="totals")

        self.total_sessions = TotalTile(cards, "Sessions", theme.TEXT)
        self.total_sessions.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.total_time = TotalTile(cards, "Time connected", theme.ACCENT)
        self.total_time.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        self.total_data = TotalTile(cards, "Data", theme.VIOLET)
        self.total_data.grid(row=0, column=2, sticky="ew", padx=(0, 8))
        self.total_rate = TotalTile(cards, "Clean exits", theme.GREEN)
        self.total_rate.grid(row=0, column=3, sticky="ew")

        split = tk.Frame(self, bg=theme.BG)
        split.pack(fill="both", expand=True, padx=28, pady=(0, 20))

        self.detail = DetailPanel(split, self._close_detail, self._copy_detail)

        self.scroll = ScrollFrame(split, bg=theme.BG)
        self.scroll.pack(side="left", fill="both", expand=True)

        self.empty = EmptyState(self.scroll.inner, "No sessions yet",
                                "Connect to a server and the session will be "
                                "logged here when it ends. Click any entry to "
                                "inspect it.")

    # ------------------------------------------------------------- rendering
    def refresh(self):
        for row in self.rows:
            row.destroy()
        self.rows = []
        self._active = None
        self.detail.pack_forget()

        for child in self.scroll.inner.winfo_children():
            child.destroy()

        entries = history.load()
        stats = history.totals(entries)
        self.total_sessions.set(str(stats["count"]))
        self.total_time.set(_duration(stats["seconds"]))
        self.total_data.set(_size(stats["down"] + stats["up"]))
        self.total_rate.set("%.0f%%" % stats["rate"],
                            theme.GREEN if stats["rate"] >= 80 else
                            theme.AMBER if stats["rate"] >= 50 else theme.RED)
        self.count_label.configure(text="%d sessions" % stats["count"])

        if not entries:
            self.empty.pack(pady=40)
            return

        self.empty.pack_forget()
        last_day = None
        for entry in entries:
            day = _day_label(entry.get("started"))
            if day != last_day:
                DayHeader(self.scroll.inner, day).pack(fill="x", pady=(10, 2))
                last_day = day
            row = HistoryRow(self.scroll.inner, entry, self._open)
            row.pack(fill="x", pady=2)
            self.rows.append(row)

    def _open(self, row):
        if self._active is not None:
            self._active.set_selected(False)
        self._active = row
        row.set_selected(True)
        self.detail.show(row.entry)
        if not self.detail.winfo_ismapped():
            self.detail.pack(side="right", fill="y", padx=(12, 0))

    def _close_detail(self):
        if self._active is not None:
            self._active.set_selected(False)
            self._active = None
        self.detail.pack_forget()

    def _copy_detail(self):
        entry = self.detail.entry
        if not entry:
            return
        block = "\n".join([
            "Server   : %s" % (entry.get("server") or "?"),
            "Endpoint : %s:%s" % (entry.get("host") or "?",
                                  entry.get("port") or "?"),
            "Protocol : %s" % ((entry.get("proto") or "?").upper()),
            "Tunnel IP: %s" % (entry.get("tunnel_ip") or "-"),
            "Exit IP  : %s" % (entry.get("exit_ip") or "-"),
            "Started  : %s" % _stamp(entry.get("started")),
            "Ended    : %s" % _stamp(entry.get("ended")),
            "Duration : %s" % _duration(entry.get("seconds") or 0),
            "Outcome  : %s" % (entry.get("outcome") or "?"),
        ])
        try:
            self.clipboard_clear()
            self.clipboard_append(block)
            self.app.toast("Session details copied", "good")
        except tk.TclError:
            pass

    def _clear(self):
        history.clear()
        self.refresh()
        self.app.toast("History cleared", "info")

    def _export(self):
        path = filedialog.asksaveasfilename(defaultextension=".txt",
                                            initialfile="oxyvpn_history.txt")
        if not path:
            return
        entries = history.load(history.MAX_ENTRIES)
        lines = ["OxyVPN session history", ""]
        for entry in entries:
            lines.append("%s  %s  %s:%s  %s  %s  %s"
                         % (_stamp(entry.get("started")),
                            entry.get("server", "?"),
                            entry.get("host", "?"), entry.get("port", "?"),
                            (entry.get("proto") or "?").upper(),
                            _duration(entry.get("seconds") or 0),
                            entry.get("outcome", "?")))
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines))
        self.app.toast("History exported", "good")