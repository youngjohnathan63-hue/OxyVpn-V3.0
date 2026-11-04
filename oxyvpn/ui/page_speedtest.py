"""Throughput test page with an analogue gauge."""

from __future__ import annotations

import math
import threading
import tkinter as tk

from .. import speedtest
from ..netinfo import probe_latency
from . import theme
from .widgets import Eyebrow, FlatButton

SCALE_MAX = 100.0
START_ANGLE = 225.0
SWEEP = -270.0


def _ratio(mbps):
    if mbps <= 0:
        return 0.0
    scaled = math.log10(1.0 + min(mbps, SCALE_MAX * 4)) / math.log10(1.0 + SCALE_MAX)
    return max(0.0, min(1.0, scaled))


def _colour(mbps):
    if mbps < 0:
        return theme.TEXT_FAINT
    if mbps >= 50:
        return theme.GREEN
    if mbps >= 15:
        return theme.ACCENT
    if mbps >= 5:
        return theme.AMBER
    return theme.RED


class SpeedGauge(tk.Canvas):
    """270-degree dial with needle, ticks and a live centre readout."""

    SIZE = 300

    def __init__(self, master, bg=None):
        bg = bg or theme.BG
        super().__init__(master, width=self.SIZE, height=self.SIZE, bg=bg,
                         highlightthickness=0, bd=0)
        self._bg = bg
        self._value = 0.0
        self._peak = 0.0
        self._colour = theme.ACCENT
        self._label = "READY"
        self.bind("<Configure>", lambda e: self.redraw())
        self.redraw()

    def _cx(self):
        return self.SIZE / 2.0

    def reset(self, label="READY"):
        self._value = 0.0
        self._peak = 0.0
        self._colour = theme.ACCENT
        self._label = label
        self.redraw()

    def set_value(self, mbps, label=None):
        self._value = max(0.0, mbps)
        self._peak = max(self._peak, self._value)
        self._colour = _colour(self._value)
        if label is not None:
            self._label = label
        self.redraw()

    def set_label(self, label):
        self._label = label
        self.redraw()

    def redraw(self):
        self.delete("all")
        size = self.SIZE
        cx = cy = size / 2.0
        radius = size * 0.40
        box = (cx - radius, cy - radius, cx + radius, cy + radius)

        self.create_arc(*box, start=START_ANGLE, extent=SWEEP, style="arc",
                        outline=theme.SURFACE_HI, width=10)

        for index in range(0, 11):
            angle = math.radians(START_ANGLE + SWEEP * (index / 10.0))
            inner = radius - 16
            outer = radius - 8
            self.create_line(cx + math.cos(angle) * inner,
                             cy - math.sin(angle) * inner,
                             cx + math.cos(angle) * outer,
                             cy - math.sin(angle) * outer,
                             fill=theme.BORDER_HI if index % 5 else theme.TEXT_FAINT,
                             width=1)

        if self._value > 0:
            self.create_arc(*box, start=START_ANGLE,
                            extent=SWEEP * _ratio(self._value), style="arc",
                            outline=self._colour, width=10)

        if self._peak > 0:
            angle = math.radians(START_ANGLE + SWEEP * _ratio(self._peak))
            self.create_line(cx + math.cos(angle) * (radius - 20),
                             cy - math.sin(angle) * (radius - 20),
                             cx + math.cos(angle) * (radius + 6),
                             cy - math.sin(angle) * (radius + 6),
                             fill=theme.TEXT_FAINT, width=2)

        angle = math.radians(START_ANGLE + SWEEP * _ratio(self._value))
        self.create_line(cx, cy,
                         cx + math.cos(angle) * (radius - 26),
                         cy - math.sin(angle) * (radius - 26),
                         fill=self._colour, width=3)
        self.create_oval(cx - 5, cy - 5, cx + 5, cy + 5,
                         fill=self._colour, outline=self._bg, width=2)

        if self._value > 0:
            text = "%.1f" % self._value
        else:
            text = "--"
        self.create_text(cx, cy + radius * 0.62, text=text,
                         fill=self._colour if self._value > 0 else theme.TEXT_MUTED,
                         font=theme.f(34, "bold"))
        self.create_text(cx, cy + radius * 0.62 + 30, text="Mbps",
                         fill=theme.TEXT_FAINT, font=theme.f(theme.S9, "bold"))
        self.create_text(cx, cy - radius * 0.42, text=self._label,
                         fill=theme.TEXT_FAINT, font=theme.f(theme.S8, "bold"))


class Readout(tk.Canvas):
    """Fixed-height label/value pill."""

    HEIGHT = 58

    def __init__(self, master, label, bg=None):
        bg = bg or theme.BG
        super().__init__(master, height=self.HEIGHT, bg=bg,
                         highlightthickness=0, bd=0)
        self._label = label
        self._value = "--"
        self._colour = theme.TEXT_MUTED
        self.bind("<Configure>", lambda e: self.redraw())

    def set(self, value, colour=None):
        self._value = value
        self._colour = colour or theme.TEXT
        self.redraw()

    def redraw(self):
        from .widgets import round_rect
        self.delete("all")
        width = self.winfo_width()
        if width < 20:
            return
        round_rect(self, 1, 1, width - 2, self.HEIGHT - 2, theme.RADIUS_SM,
                   theme.SURFACE, theme.BORDER, 1)
        self.create_text(13, 17, text=self._label.upper(), fill=theme.TEXT_FAINT,
                         font=theme.f(theme.S8, "bold"), anchor="w")
        self.create_text(13, 38, text=self._value, fill=self._colour,
                         font=theme.f(theme.S18, "bold"), anchor="w")


class SpeedTestPage(tk.Frame):
    def __init__(self, master, app):
        super().__init__(master, bg=theme.BG)
        self.app = app
        self._running = False
        self._stop = False

        header = tk.Frame(self, bg=theme.BG)
        header.pack(fill="x", padx=28, pady=(18, 6))
        Eyebrow(header, "Diagnostics").pack(fill="x")
        line = tk.Frame(header, bg=theme.BG)
        line.pack(fill="x", pady=(2, 0))
        tk.Label(line, text="Speed test", bg=theme.BG, fg=theme.TEXT,
                 font=theme.f(theme.S28, "bold")).pack(side="left")
        self.run_button = FlatButton(line, "Start test", self._toggle, kind="accent")
        self.run_button.pack(side="right", pady=(6, 0))

        self.gauge = SpeedGauge(self)
        self.gauge.pack(pady=(2, 6))

        readouts = tk.Frame(self, bg=theme.BG)
        readouts.pack(fill="x", padx=28)
        for column in range(3):
            readouts.columnconfigure(column, weight=1, uniform="readout")

        self.ping = Readout(readouts, "Ping")
        self.ping.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.down = Readout(readouts, "Download")
        self.down.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        self.up = Readout(readouts, "Upload")
        self.up.grid(row=0, column=2, sticky="ew")

        self.progress = tk.Canvas(self, height=4, bg=theme.SURFACE_HI,
                                  highlightthickness=0, bd=0)
        self.progress.pack(fill="x", padx=28, pady=(12, 0))
        self._bar = self.progress.create_rectangle(0, 0, 0, 4,
                                                   fill=theme.ACCENT, outline="")

        self.status = tk.Label(self, text="Idle - press Start test",
                               bg=theme.BG, fg=theme.TEXT_FAINT,
                               font=theme.m(theme.S8), anchor="w")
        self.status.pack(fill="x", padx=28, pady=(7, 0))

        tk.Label(self,
                 text="Traffic goes to speed.cloudflare.com through the active "
                      "tunnel. Compare servers, or run it disconnected for a "
                      "baseline. TCP 443 tunnels read lower than UDP.",
                 bg=theme.BG, fg=theme.TEXT_FAINT, font=theme.f(theme.S8),
                 anchor="w", justify="left", wraplength=620).pack(
            fill="x", padx=28, pady=(12, 18))

    def _toggle(self):
        if self._running:
            self._stop = True
            self.status.configure(text="stopping...", fg=theme.AMBER)
            return
        self._start()

    def _start(self):
        self._running = True
        self._stop = False
        self.run_button.configure(text="Stop")
        self.gauge.reset("PING")
        self.ping.set("--", theme.VIOLET)
        self.down.set("--", theme.GREEN)
        self.up.set("--", theme.ACCENT)
        self.progress.coords(self._bar, 0, 0, 0, 4)
        self.status.configure(text="measuring latency", fg=theme.TEXT_FAINT)
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        latency = -1.0
        profile = self.app.selected
        if self.app.session.status.is_up and profile is not None:
            latency = probe_latency(profile.host, profile.port, profile.proto, 2.0)

        peak = [0.0]

        def progress(done, total, mbps):
            peak[0] = max(peak[0], mbps)
            self.app.post(lambda d=done, t=total, m=mbps: self._progress(d, t, m))

        if not self._stop:
            self.app.post(lambda: (self.gauge.set_label("DOWNLOAD"),
                                   self.status.configure(text="measuring download",
                                                         fg=theme.TEXT_FAINT)))
        down = speedtest.download(on_progress=progress,
                                  should_stop=lambda: self._stop)

        up = -1.0
        if not self._stop:
            self.app.post(lambda: (self.gauge.set_label("UPLOAD"),
                                   self.progress.coords(self._bar, 0, 0, 0, 4),
                                   self.status.configure(text="measuring upload",
                                                         fg=theme.TEXT_FAINT)))
            up = speedtest.upload(should_stop=lambda: self._stop)

        self.app.post(lambda: self._done(latency, down, up))

    def _progress(self, done, total, mbps):
        try:
            self.gauge.set_value(mbps)
            width = max(1, self.progress.winfo_width())
            ratio = min(1.0, done / float(max(1, total)))
            self.progress.coords(self._bar, 0, 0, width * ratio, 4)
        except tk.TclError:
            pass

    def _done(self, latency, down, up):
        self._running = False
        self._stop = False
        try:
            self.run_button.configure(text="Start test")
        except tk.TclError:
            pass

        if latency > 0:
            self.ping.set("%d ms" % int(latency),
                          theme.GREEN if latency < 90 else
                          theme.AMBER if latency < 200 else theme.RED)
        else:
            self.ping.set("n/a", theme.TEXT_FAINT)

        self.down.set("%.1f Mbps" % down if down >= 0 else "failed",
                      _colour(down))
        self.up.set("%.1f Mbps" % up if up >= 0 else "failed", _colour(up))

        if down < 0 and up < 0:
            self.gauge.reset("FAILED")
            self.status.configure(text="test failed - check the tunnel",
                                  fg=theme.RED)
        else:
            self.gauge.set_value(down if down > 0 else up, "COMPLETE")
            self.progress.coords(self._bar, 0, 0, self.progress.winfo_width(), 4)
            self.status.configure(text="complete", fg=theme.GREEN)
            self.app.log_line("speed test: %s down / %s up / %s ms"
                              % ("%.1f" % down if down >= 0 else "n/a",
                                 "%.1f" % up if up >= 0 else "n/a",
                                 int(latency) if latency > 0 else "n/a"))