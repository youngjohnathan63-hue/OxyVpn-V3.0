"""Primary connection page: hero control plus a live telemetry row."""

from __future__ import annotations

import tkinter as tk

from . import theme
from .icons import ICONS
from .widgets import (Card, ConnectButton, Eyebrow, FlatButton, PhaseTracker,
                      RadialBackdrop, Sparkline, StatTile)


class ConnectPage(tk.Frame):
    def __init__(self, master, app):
        super().__init__(master, bg=theme.BG)
        self.app = app

        wrap = tk.Frame(self, bg=theme.BG)
        wrap.pack(fill="both", expand=True, padx=28, pady=(18, 20))
        wrap.columnconfigure(0, weight=1)
        wrap.rowconfigure(1, weight=1)

        header = tk.Frame(wrap, bg=theme.BG)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        Eyebrow(header, "Tunnel").pack(fill="x")
        line = tk.Frame(header, bg=theme.BG)
        line.pack(fill="x", pady=(2, 0))
        tk.Label(line, text="Connection", bg=theme.BG, fg=theme.TEXT,
                 font=theme.f(theme.S28, "bold"), anchor="w").pack(side="left")
        self.state_pill = tk.Label(line, text="IDLE", bg=theme.SURFACE_HI,
                                   fg=theme.TEXT_MUTED, font=theme.f(theme.S8, "bold"),
                                   padx=10, pady=4)
        self.state_pill.pack(side="right", pady=(10, 0))
        FlatButton(line, "Restore internet", self.app.restore_internet,
                   kind="ghost").pack(side="right", padx=(0, 10), pady=(6, 0))
        self.quick = FlatButton(line, "Quick connect", self.app.quick_connect,
                                kind="accent")
        self.quick.pack(side="right", padx=(0, 8), pady=(6, 0))

        hero = tk.Frame(wrap, bg=theme.BG)
        hero.grid(row=1, column=0, sticky="nsew", pady=(0, 14))

        self.backdrop = RadialBackdrop(hero, bg=theme.BG)
        self.backdrop.place(x=0, y=0, relwidth=1, relheight=1)

        inner = tk.Frame(hero, bg=theme.BG)
        inner.place(relx=0.5, rely=0.5, anchor="center")

        self.button = ConnectButton(inner, size=186, command=self.app.toggle_connection)
        self.button.pack()

        self.headline = tk.Label(inner, text="Not connected", bg=theme.BG,
                                 fg=theme.TEXT, font=theme.f(theme.S22, "bold"))
        self.headline.pack(pady=(12, 0))
        self.subline = tk.Label(inner, text="Pick a server and hit connect",
                                bg=theme.BG, fg=theme.TEXT_MUTED, font=theme.f(theme.S10),
                                wraplength=460, justify="center")
        self.subline.pack(pady=(4, 0))

        self.phases = PhaseTracker(inner, bg=theme.BG)
        self.phases.pack(fill="x", padx=30, pady=(12, 0))

        self.chips = tk.Frame(inner, bg=theme.BG)
        self.chips.pack(pady=(10, 0))
        self._chip("lock", "Kill switch", self._setting("kill_switch"))
        self._chip("shield", "DNS guard", self._setting("block_dns"))
        self._chip("globe", "IPv6 guard", self._setting("block_ipv6"))
        self._chip("key", "Strict crypto", self._setting("crypto_hardening"))

        rail = tk.Frame(wrap, bg=theme.BG)
        rail.grid(row=2, column=0, sticky="ew")
        for column in range(3):
            rail.columnconfigure(column, weight=1, uniform="rail")

        server_card = Card(rail, pad=15, title="Active server")
        server_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        row = tk.Frame(server_card.body, bg=theme.SURFACE)
        row.pack(fill="x")
        self.flag = tk.Canvas(row, width=36, height=24, bg=theme.SURFACE,
                              highlightthickness=0, bd=0)
        self.flag.pack(side="left")
        self._flag_code = ""
        self.server_name = tk.Label(row, text="None selected", bg=theme.SURFACE,
                                    fg=theme.TEXT, font=theme.f(theme.S11, "bold"),
                                    anchor="w")
        self.server_name.pack(side="left", padx=10)

        self.server_detail = tk.Label(server_card.body, text="", bg=theme.SURFACE,
                                      fg=theme.TEXT_FAINT, font=theme.m(theme.S8),
                                      anchor="w")
        self.server_detail.pack(fill="x", pady=(8, 10))
        FlatButton(server_card.body, "Change server",
                   lambda: self.app.show_page("servers")).pack(fill="x")

        traffic_card = Card(rail, pad=15, title="Throughput")
        traffic_card.grid(row=0, column=1, sticky="nsew", padx=(0, 10))
        self.graph = Sparkline(traffic_card.body, height=44, bg=theme.SURFACE)
        self.graph.pack(fill="x", pady=(0, 12))

        pair = tk.Frame(traffic_card.body, bg=theme.SURFACE)
        pair.pack(fill="x")
        pair.columnconfigure(0, weight=1)
        pair.columnconfigure(1, weight=1)
        self.down = StatTile(pair, "Download", "0 B/s", theme.GREEN)
        self.down.grid(row=0, column=0, sticky="w")
        self.up = StatTile(pair, "Upload", "0 B/s", theme.ACCENT)
        self.up.grid(row=0, column=1, sticky="w")

        session_card = Card(rail, pad=15, title="Session")
        session_card.grid(row=0, column=2, sticky="nsew")
        trio = tk.Frame(session_card.body, bg=theme.SURFACE)
        trio.pack(fill="x")
        for column in range(3):
            trio.columnconfigure(column, weight=1)
        self.uptime = StatTile(trio, "Uptime", "00:00:00")
        self.uptime.grid(row=0, column=0, sticky="w")
        self.data = StatTile(trio, "Data", "0 B", theme.VIOLET)
        self.data.grid(row=0, column=1, sticky="w")
        self.exit_ip = StatTile(trio, "Exit IP", "checking", theme.AMBER)
        self.exit_ip.grid(row=0, column=2, sticky="w")

        self.exit_ip.value.configure(cursor="hand2")
        self.exit_ip.value.bind("<Button-1>", self._copy_ip)
        self._ip_text = ""

    def _copy_ip(self, _event=None):
        if not self._ip_text:
            return
        try:
            self.clipboard_clear()
            self.clipboard_append(self._ip_text.split()[0])
            self.app.toast("Exit IP copied", "good")
        except tk.TclError:
            pass

    def _setting(self, name):
        try:
            return bool(getattr(self.app.store.data, name))
        except Exception:
            return False

    def _chip(self, icon, text, enabled):
        holder = tk.Frame(self.chips, bg=theme.BG)
        holder.pack(side="left", padx=(0, 8))
        colour = theme.GREEN if enabled else theme.TEXT_FAINT
        box = tk.Frame(holder, bg=theme.SURFACE, highlightthickness=1,
                       highlightbackground=theme.BORDER)
        box.pack()
        glyph = tk.Canvas(box, width=12, height=12, bg=theme.SURFACE,
                          highlightthickness=0, bd=0)
        glyph.pack(side="left", padx=(7, 4), pady=4)
        ICONS[icon](glyph, 6, 6, 10, colour, 1.4)
        tk.Label(box, text=text, bg=theme.SURFACE, fg=colour,
                 font=theme.f(theme.S8, "bold"), padx=0, pady=3).pack(
            side="left", padx=(0, 7))

    def _paint_flag(self):
        from .widgets import draw_flag
        self.flag.delete("all")
        draw_flag(self.flag, 18, 12, 34, 22, self._flag_code)

    @staticmethod
    def _phase_for(text):
        lowered = (text or "").lower()
        if "prepar" in lowered or "locating" in lowered:
            return 0
        if "connect" in lowered or "starting" in lowered or "tunnel" in lowered:
            return 1
        if "auth" in lowered:
            return 2
        if "config" in lowered:
            return 3
        if "assign" in lowered or "address" in lowered or "route" in lowered:
            return 4
        return -1

    def set_profile(self, profile):
        if profile is None:
            self._flag_code = ""
            self.server_name.configure(text="None selected")
            self.server_detail.configure(text="")
            self._paint_flag()
            return
        self._flag_code = (profile.country_code or "").lower()
        self.server_name.configure(text=profile.title)
        self.server_detail.configure(text=profile.subtitle)
        self._paint_flag()

    def set_state(self, state, headline, subline):
        self.button.set_state({"connected": "connected", "failed": "failed",
                               "connecting": "connecting"}.get(state, "idle"))
        self.headline.configure(text=headline)
        self.subline.configure(text=subline)

        colour, pill = {
            "connected": (theme.GREEN, "CONNECTED"),
            "failed": (theme.RED, "FAILED"),
            "connecting": (theme.ACCENT, "WORKING"),
        }.get(state, (theme.TEXT_MUTED, "IDLE"))
        self.state_pill.configure(text=pill, fg=colour,
                                  bg=theme.fade(colour, theme.SURFACE_HI, 0.24))
        self.backdrop.set_colour(colour)

        if state == "connected":
            self.phases.set_phase(6, theme.GREEN)
        elif state == "connecting":
            self.phases.set_phase(self._phase_for(headline), colour)
        else:
            self.phases.set_phase(-1)

    def set_traffic(self, down_bps, up_bps):
        self.down.set(self._rate(down_bps))
        self.up.set(self._rate(up_bps))
        self.graph.push(down_bps)

    def set_totals(self, down_bytes, up_bytes):
        self.data.set(self._size(down_bytes + up_bytes))

    def set_uptime(self, seconds):
        self.uptime.set("%02d:%02d:%02d" % (int(seconds // 3600),
                                            int((seconds % 3600) // 60),
                                            int(seconds % 60)))

    def set_exit_ip(self, text, colour=None):
        self._ip_text = text or ""
        self.exit_ip.set(text, colour)

    @staticmethod
    def _rate(bps):
        if bps < 1024:
            return "%d B/s" % bps
        if bps < 1024 * 1024:
            return "%.1f KB/s" % (bps / 1024.0)
        return "%.2f MB/s" % (bps / (1024.0 * 1024.0))

    @staticmethod
    def _size(total):
        total = max(0, total)
        if total < 1024:
            return "%d B" % total
        if total < 1024 * 1024:
            return "%.1f KB" % (total / 1024.0)
        if total < 1024 * 1024 * 1024:
            return "%.1f MB" % (total / (1024.0 * 1024.0))
        return "%.2f GB" % (total / (1024.0 * 1024.0 * 1024.0))