"""Application shell: window, navigation, session wiring."""

from __future__ import annotations

import queue
import shutil
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog

from .. import __version__
from ..admin import is_admin, relaunch_elevated
from ..killswitch import KillSwitch
from ..netinfo import (default_gateway, dns_servers, lookup_public_ip,
                       physical_ipv4_addresses, probe_latency, resolve, valid_ip)
from ..paths import default_profiles_dir, ensure_dirs
from ..store import SettingsStore
from ..vpn import history
from ..vpn.profile import prune_generated, scan_profiles
from ..vpn.session import VpnState, VpnSession
from . import branding, theme
from .page_connect import ConnectPage
from .page_history import HistoryPage
from .page_logs import LogsPage
from .page_scanner import ScannerPage
from .page_servers import ServersPage
from .page_settings import SettingsPage
from .page_speedtest import SpeedTestPage
from .widgets import NavItem, SessionCard
from .window import FramelessWindow, enable_dpi_awareness

PAGE_ORDER = ["connect", "scanner", "servers", "speedtest", "history",
              "settings", "logs"]
PAGE_LABELS = {
    "connect": ("Connect", "power"),
    "scanner": ("Scanner", "shield"),
    "servers": ("Servers", "globe"),
    "speedtest": ("Speed test", "bolt"),
    "history": ("History", "clock"),
    "settings": ("Settings", "gear"),
    "logs": ("Logs", "terminal"),
}
NAV_GROUPS = [
    ("TUNNEL", ["connect", "servers"]),
    ("TOOLS", ["scanner", "speedtest", "history", "settings", "logs"]),
]
MAX_AUTO_RETRIES = 2
MAX_DROPS = 5
DROP_DELAY = 2000
SAFE_MODE_AFTER = 1
HEALTH_DELAY = 8000
HEALTH_TRIES = 3
QUICK_LIMIT = 18
QUICK_TIMEOUT = 1.5
AUTOSTART_DELAY = 1500


class App:
    def __init__(self, window: FramelessWindow):
        ensure_dirs()
        self.window = window
        self.store = SettingsStore()
        self.events = queue.Queue()
        self.profiles = []
        self.selected = None
        self._closing = False
        self._connecting = False
        self._pending = None
        self._auto_retries = 0
        self._drops = 0
        self._user_disconnect = False
        self._quick_busy = False
        self._server_ip = ""
        self._toast = None
        self._last_toast = ""
        self._scan_score = None
        self._session_start = 0.0
        self._session_title = ""
        self._session_bytes = (0, 0)
        self._session_profile = None
        self._last_exit_ip = ""

        self.killswitch = KillSwitch()
        self.session = VpnSession(
            on_state=lambda status: self.events.put(("state", status)),
            on_log=lambda message: self.events.put(("log", message)),
            on_traffic=lambda down, up: self.events.put(("traffic", down, up)),
        )

        self._build()
        self._wire()
        self.reload_profiles()
        self._restore_selection()
        self._cleanup_stale()
        self.window.after(80, self._drain)
        self.window.after(400, self._start_ip_watch)
        self.window.after(1000, self._tick)
        self.window.after(AUTOSTART_DELAY, self._maybe_autostart)

    def _build(self):
        self.window.build_chrome("OxyVPN", "v" + __version__)
        if self.store.data.window_geometry:
            self.window.apply_saved_geometry(self.store.data.window_geometry)

        self.window.build_statusbar()

        body = tk.Frame(self.window.content, bg=theme.BG)
        body.pack(fill="both", expand=True)

        sidebar = tk.Frame(body, bg=theme.BG_ALT, width=228)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        tk.Frame(sidebar, bg=theme.HAIRLINE, width=1).pack(side="right", fill="y")

        brand = tk.Frame(sidebar, bg=theme.BG_ALT)
        brand.pack(fill="x", padx=18, pady=(20, 18))

        self.brand_tile = tk.Canvas(brand, width=40, height=40, bg=theme.BG_ALT,
                                    highlightthickness=0, bd=0)
        self.brand_tile.pack(side="left")
        branding.draw(self.brand_tile, 20, 20, 40)

        names = tk.Frame(brand, bg=theme.BG_ALT)
        names.pack(side="left", padx=(12, 0))
        tk.Label(names, text="OxyVPN", bg=theme.BG_ALT, fg=theme.TEXT,
                 font=theme.f(theme.S15, "bold"), anchor="w").pack(fill="x")
        tk.Label(names, text="OpenVPN client", bg=theme.BG_ALT, fg=theme.TEXT_FAINT,
                 font=theme.f(theme.S8), anchor="w").pack(fill="x", pady=(1, 0))

        self.nav = {}
        for group, keys in NAV_GROUPS:
            tk.Label(sidebar, text=group, bg=theme.BG_ALT, fg=theme.TEXT_FAINT,
                     font=theme.f(theme.S8, "bold"), anchor="w").pack(
                fill="x", padx=26, pady=(10, 6))
            for key in keys:
                label, icon = PAGE_LABELS[key]
                item = NavItem(sidebar, label, icon, lambda k=key: self.show_page(k))
                item.pack(fill="x", padx=8, pady=2)
                self.nav[key] = item

        footer = tk.Frame(sidebar, bg=theme.BG_ALT)
        footer.pack(side="bottom", fill="x", padx=20, pady=16)

        status_row = tk.Frame(footer, bg=theme.BG_ALT)
        status_row.pack(fill="x")
        self._priv_dot = tk.Canvas(status_row, width=8, height=8, bg=theme.BG_ALT,
                                   highlightthickness=0, bd=0)
        self._priv_dot.pack(side="left", padx=(0, 6), pady=3)
        self._priv_oval = self._priv_dot.create_oval(1, 1, 7, 7, fill=theme.AMBER,
                                                     outline=theme.AMBER)
        self.privilege = tk.Label(status_row, text="", bg=theme.BG_ALT,
                                  fg=theme.TEXT_FAINT, font=theme.f(theme.S8),
                                  anchor="w")
        self.privilege.pack(side="left")

        tk.Label(footer, text="OpenVPN front-end", bg=theme.BG_ALT,
                 fg=theme.TEXT_FAINT, font=theme.f(theme.S8), anchor="w").pack(
            fill="x", pady=(4, 0))

        self.session_card = SessionCard(sidebar)
        self.session_card.pack(side="bottom", fill="x", padx=12, pady=(0, 6))

        self.container = tk.Frame(body, bg=theme.BG)
        self.container.pack(side="left", fill="both", expand=True)

        self.pages = {
            "connect": ConnectPage(self.container, self),
            "scanner": ScannerPage(self.container, self),
            "servers": ServersPage(self.container, self),
            "speedtest": SpeedTestPage(self.container, self),
            "history": HistoryPage(self.container, self),
            "settings": SettingsPage(self.container, self),
            "logs": LogsPage(self.container, self),
        }
        for page in self.pages.values():
            page.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.show_page("connect")

    def _wire(self):
        self.window.on_close = self.shutdown
        elevated = is_admin()
        self.privilege.configure(
            text="Administrator" if elevated else "Not elevated",
            fg=theme.GREEN if elevated else theme.AMBER)
        colour = theme.GREEN if elevated else theme.AMBER
        self._priv_dot.itemconfigure(self._priv_oval, fill=colour, outline=colour)
        self._bind_shortcuts()

    def _bind_shortcuts(self):
        for index, key in enumerate(PAGE_ORDER, start=1):
            self.window.bind("<Control-Key-%d>" % index,
                             lambda e, k=key: (self.show_page(k), "break")[1])
        self.window.bind("<Control-Return>",
                         lambda e: (self.toggle_connection(), "break")[1])
        self.window.bind("<Control-Shift-Q>",
                         lambda e: (self.quick_connect(), "break")[1])
        self.window.bind("<Escape>", lambda e: (self._escape(), "break")[1])

    def _escape(self):
        if self.session.status.state.busy or self._connecting:
            self._pending = None
            self._user_disconnect = True
            self.session.abort()
            self._connecting = False
            self.pages["connect"].set_state("idle", "Not connected",
                                            "Pick a server and hit connect")
            self.session_card.update_state("idle")
            self.window.set_status("Disconnected", theme.TEXT_FAINT)
            self._disarm_killswitch()
        elif self._toast is not None:
            self._kill_toast(self._toast)

    def post(self, callback):
        self.events.put(("call", callback))

    def log_line(self, text):
        self.post(lambda t=text: self.pages["logs"].append(t))

    def profiles_dir(self):
        return Path(self.store.data.profiles_dir or default_profiles_dir())

    def profiles_dir_text(self):
        return str(self.profiles_dir())

    def show_page(self, key):
        for name, item in self.nav.items():
            item.set_active(name == key)
        self.pages[key].lift()
        if key == "servers":
            self.pages["servers"].refresh()
        elif key == "history":
            self.pages["history"].refresh()

    def reload_profiles(self):
        self.profiles = scan_profiles(self.profiles_dir())
        if "servers" in self.pages:
            self.pages["servers"].refresh()

    def prune_pinned(self):
        removed = prune_generated(self.profiles_dir())
        if removed:
            self.reload_profiles()
            self.pages["logs"].append("removed %d pinned profile copies" % removed)
        return removed

    def import_profiles(self):
        chosen = filedialog.askopenfilenames(
            title="Add OpenVPN profiles",
            filetypes=[("OpenVPN config", "*.ovpn"), ("All files", "*.*")])
        if not chosen:
            return

        target = self.profiles_dir()
        try:
            target.mkdir(parents=True, exist_ok=True)
        except OSError:
            self.toast("Could not create the profiles folder", "bad")
            return

        copied = 0
        for raw in chosen:
            source = Path(raw)
            destination = target / source.name
            if destination.exists() or not source.is_file():
                continue
            try:
                shutil.copy2(source, destination)
                copied += 1
            except OSError:
                pass

        self.reload_profiles()
        warned = sum(1 for p in self.profiles if p.issues)
        if copied:
            self.toast("%d profile(s) added" % copied, "good")
            if warned:
                self.toast("%d profile(s) have config warnings" % warned, "warn")
        else:
            self.toast("Nothing copied - files already present", "warn")

    def _maybe_autostart(self):
        if self._closing or not self.store.data.auto_connect:
            return
        if self.session.status.state != VpnState.IDLE:
            return
        if not self.store.data.username or not self.store.data.password:
            return
        if not self.profiles:
            return
        self.log_line("auto-connect on launch")
        if self.selected is not None:
            self.connect_to(self.selected)
        else:
            self.quick_connect()

    def _restore_selection(self):
        last = self.store.data.last_server
        for profile in self.profiles:
            if profile.key == last:
                self.selected = profile
                break
        if self.selected is None and self.profiles:
            self.selected = self.profiles[0]
        self.pages["connect"].set_profile(self.selected)

    def select_profile(self, profile):
        self.selected = profile
        self.store.update(last_server=profile.key)
        self.pages["connect"].set_profile(profile)
        for row in self.pages["servers"].rows:
            row.set_selected(row.profile is profile)
        if profile.issues:
            self.toast("%d config warning(s): %s"
                       % (len(profile.issues), profile.issues[0]), "warn")

    def toggle_favorite(self, profile):
        favorites = list(self.store.data.favorites or [])
        if profile.key in favorites:
            favorites.remove(profile.key)
            self.toast("Removed from favorites", "info")
        else:
            favorites.append(profile.key)
            self.toast("Added to favorites", "good")
        self.store.update(favorites=favorites)
        self.pages["servers"].refresh()

    def set_scan_score(self, score, grade):
        self._scan_score = (score, grade)
        self.window.set_status_extra(scan="scan %d/100 (%s)" % (score, grade))

    def _cleanup_stale(self):
        try:
            if self.killswitch.present():
                self.killswitch.clear()
                self.pages["logs"].append("removed stale kill-switch rules")
        except Exception:
            pass

    def _start_ip_watch(self):
        threading.Thread(target=self._ip_worker, daemon=True).start()

    def _ip_worker(self):
        info = lookup_public_ip()

        def show():
            if info.ok:
                self._last_exit_ip = info.ip
                text = info.ip + ("  (%s)" % info.country if info.country else "")
                self.pages["connect"].set_exit_ip(text, theme.AMBER)
            else:
                self.pages["connect"].set_exit_ip("unavailable", theme.TEXT_FAINT)

        self.post(show)

    def toast(self, text, kind="info"):
        self.post(lambda: self._toast_now(text, kind))

    def _toast_now(self, text, kind):
        if text == self._last_toast:
            try:
                if self._toast is not None:
                    self._toast.destroy()
            except Exception:
                pass
        self._last_toast = text

        colours = {
            "info": (theme.SURFACE_HI, theme.TEXT, theme.BORDER_HI),
            "good": (theme.GREEN_DIM, theme.GREEN, theme.GREEN),
            "bad": (theme.RED_DIM, theme.RED, theme.RED),
            "warn": (theme.AMBER_DIM, theme.AMBER, theme.AMBER),
        }
        bg, fg, border = colours.get(kind, colours["info"])
        try:
            if self._toast is not None:
                self._toast.destroy()
        except Exception:
            pass
        frame = tk.Frame(self.window.content, bg=bg, highlightthickness=1,
                         highlightbackground=border)
        tk.Label(frame, text=text, bg=bg, fg=fg, font=theme.f(theme.S9, "bold"),
                 padx=18, pady=9).pack()
        frame.place(relx=0.5, y=16, anchor="n")
        frame.lift()
        self._toast = frame
        self.window.after(theme.TOAST_MS, lambda f=frame: self._kill_toast(f))

    def _kill_toast(self, frame):
        try:
            frame.destroy()
            if frame is self._toast:
                self._toast = None
        except Exception:
            pass

    def restore_internet(self):
        try:
            self.killswitch.clear()
        except Exception:
            pass
        self.toast("Firewall rules cleared - internet restored", "good")
        self.pages["logs"].append("kill-switch rules removed manually")

    # --------------------------------------------------------- quick connect
    def quick_connect(self):
        if self._quick_busy or self.session.status.state.busy or self._connecting:
            return
        if not self.profiles:
            self.show_page("servers")
            self.toast("Add .ovpn profiles first", "warn")
            return

        favorites = set(self.store.data.favorites or [])
        pinned = [p for p in self.profiles if p.key in favorites]
        rest = [p for p in self.profiles if p.key not in favorites]
        pool = (pinned + rest)[:QUICK_LIMIT]

        self._quick_busy = True
        self.pages["connect"].set_state("connecting", "Finding fastest server",
                                        "probing %d candidates" % len(pool))
        self.window.set_status("Finding fastest server", theme.ACCENT)
        threading.Thread(target=self._quick_worker, args=(pool,), daemon=True).start()

    def _quick_worker(self, pool):
        results = []
        lock = threading.Lock()

        def probe(profile):
            ms = probe_latency(profile.host, profile.port, profile.proto,
                               QUICK_TIMEOUT)
            with lock:
                results.append((ms, profile))

        threads = [threading.Thread(target=probe, args=(p,), daemon=True)
                   for p in pool]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=4.0)

        reachable = [(ms, p) for ms, p in results if ms > 0]
        if reachable:
            best = min(reachable, key=lambda item: item[0])
        elif pool:
            best = (0.0, pool[0])
        else:
            best = None

        self._quick_busy = False
        self.post(lambda b=best: self._quick_done(b))

    def _quick_done(self, best):
        if best is None:
            self.pages["connect"].set_state("idle", "Not connected",
                                            "No server profiles loaded")
            self.session_card.update_state("idle")
            self.window.set_status("Disconnected", theme.TEXT_FAINT)
            self.toast("No server profiles loaded", "bad")
            return

        ms, profile = best
        if ms > 0:
            self.log_line("quick connect: %s at %d ms" % (profile.title, int(ms)))
            self.toast("Fastest: %s (%d ms)" % (profile.title, int(ms)), "info")
        else:
            self.log_line("quick connect: latency unavailable, using %s"
                          % profile.title)
            self.toast("Latency unavailable - trying %s" % profile.title, "warn")
        self.connect_to(profile)

    # --------------------------------------------------------- kill switch
    def _arm_killswitch_async(self):
        threading.Thread(target=self._arm_killswitch, daemon=True).start()

    def _arm_killswitch(self):
        try:
            tunnel_ip = self.session.status.local_ip
            allowed = [self._server_ip] if self._server_ip else []
            allowed += dns_servers()
            gateway = default_gateway()
            if gateway:
                allowed.append(gateway)
            physical = physical_ipv4_addresses(exclude=[tunnel_ip])
            self.killswitch = KillSwitch(allowed, local_ips=physical)
            result = self.killswitch.arm()
            self.log_line(("kill switch armed: " if result.ok
                           else "kill switch failed: ") + result.detail)
        except Exception as exc:
            self.log_line("kill switch error: %s" % exc)

    def _disarm_killswitch(self):
        try:
            if self.killswitch.armed:
                self.killswitch.clear()
                self.log_line("kill switch disarmed")
        except Exception:
            pass

    def _health_check(self, attempt=1):
        info = None
        try:
            info = lookup_public_ip()
        except Exception:
            info = None

        if info is not None and info.ok:
            self._last_exit_ip = info.ip
            if info.country:
                self.post(lambda: self.pages["connect"].set_exit_ip(
                    info.ip + "  (%s)" % info.country, theme.GREEN))
            return

        if attempt < HEALTH_TRIES:
            self.log_line("health check %d/%d failed - retrying"
                          % (attempt, HEALTH_TRIES))
            self.window.after(4000, lambda a=attempt + 1: self._health_check(a))
            return

        if self.killswitch.armed:
            self._disarm_killswitch()
            self.log_line("health check failed %d times - kill switch disabled"
                          % HEALTH_TRIES)
            self.toast("Tunnel not passing traffic - kill switch disabled", "warn")

    # ---------------------------------------------------------- connection
    def toggle_connection(self):
        state = self.session.status.state
        if state == VpnState.CONNECTED or state.busy:
            self._auto_retries = 0
            self._pending = None
            self._user_disconnect = True
            self.disconnect()
        else:
            self._auto_retries = 0
            self._drops = 0
            if self.selected is None:
                self.quick_connect()
            else:
                self.connect_to(self.selected)

    def connect_to(self, profile, safe_mode=False):
        if profile is None:
            self.quick_connect()
            return
        self._pending = (profile, safe_mode)
        if self._connecting:
            self.session.abort()
            self.pages["connect"].set_state("connecting", "Switching", profile.title)
            return
        self._start_pending()

    def _start_pending(self):
        if self._pending is None or self._closing:
            return
        profile, safe_mode = self._pending
        self._pending = None
        if (self.session.status.state == VpnState.CONNECTED
                and self.session.status.profile is profile):
            self.toast("Already connected to " + profile.title, "info")
            return
        self._connecting = True
        self._user_disconnect = False
        self.selected = profile
        self.pages["connect"].set_profile(profile)
        self.store.update(last_server=profile.key)
        self.window.set_status_extra(server=profile.title)
        self.pages["connect"].set_state(
            "connecting", "Preparing" + (" (safe mode)" if safe_mode else ""),
            profile.title)
        threading.Thread(target=self._connect_worker, args=(profile, safe_mode),
                         daemon=True).start()

    def _connect_worker(self, profile, safe_mode):
        try:
            username = self.store.data.username
            password = self.store.data.password
            if not username or not password:
                self.post(lambda: self.show_page("settings"))
                self.toast("Credentials missing - fill them in Settings", "warn")
                return
            server_ip = resolve(profile.host)
            self._server_ip = server_ip
            if not server_ip:
                self.log_line("warning: could not resolve " + profile.host)

            proto = "" if safe_mode or self.store.data.proto_mode == "auto" \
                else self.store.data.proto_mode
            port = 0 if safe_mode else int(self.store.data.preferred_port or 0)
            dns = "" if safe_mode else (self.store.data.dns_override or "").strip()
            if dns and not valid_ip(dns):
                self.log_line("warning: ignoring invalid DNS override " + dns)
                dns = ""

            if self.store.data.kill_switch and server_ip:
                self.log_line("kill switch: arming before handshake")
                self._arm_killswitch()
            self.session.connect(
                profile, (username, password), self.store.data.openvpn_path,
                server_ip=server_ip,
                hardening=self.store.data.crypto_hardening and not safe_mode,
                block_dns=self.store.data.block_dns and not safe_mode,
                block_ipv6=self.store.data.block_ipv6 and not safe_mode,
                attempts=self.store.data.retry_attempts,
                proto_override=proto,
                port_override=port,
                dns_override=dns,
            )
        except Exception as exc:
            self.log_line("connect error: %s" % exc)
            self.session._fail("internal error: %s" % exc)
        finally:
            self._connecting = False
            if self._pending is not None:
                self.post(self._start_pending)

    def disconnect(self):
        self._user_disconnect = True
        self.pages["connect"].set_state("connecting", "Disconnecting", "tearing down")
        threading.Thread(target=self._disconnect_worker, daemon=True).start()

    def _disconnect_worker(self):
        self.session.disconnect()
        self._disarm_killswitch()

    def _record_session(self, outcome):
        start = self._session_start
        if not start:
            return
        self._session_start = 0.0
        now = time.time()
        down = max(0, self.session.status.bytes_in - self._session_bytes[0])
        up = max(0, self.session.status.bytes_out - self._session_bytes[1])
        profile = self._session_profile
        history.record({
            "server": self._session_title,
            "host": getattr(profile, "host", "") if profile else self._server_ip,
            "port": getattr(profile, "port", 0) if profile else 0,
            "proto": getattr(profile, "proto", "") if profile else "",
            "tunnel_ip": self.session.status.local_ip,
            "exit_ip": self._last_exit_ip,
            "kill_switch": bool(self.store.data.kill_switch),
            "started": start,
            "ended": now,
            "seconds": round(now - start, 1),
            "down": down,
            "up": up,
            "outcome": outcome,
        })
        if "history" in self.pages and self.pages["history"].winfo_ismapped():
            self.pages["history"].refresh()

    def _drain(self):
        if self._closing:
            return
        try:
            while True:
                event = self.events.get_nowait()
                kind = event[0]
                if kind == "state":
                    self._on_state(event[1])
                elif kind == "log":
                    self.pages["logs"].append(event[1])
                elif kind == "traffic":
                    self.pages["connect"].set_traffic(event[1], event[2])
                elif kind == "call":
                    try:
                        event[1]()
                    except Exception:
                        pass
        except queue.Empty:
            pass
        self.window.after(theme.DRAIN_MS, self._drain)

    def _on_state(self, status):
        state = status.state
        profile = status.profile or self.selected

        if state == VpnState.CONNECTED:
            self._auto_retries = 0
            self._drops = 0
            title = profile.title if profile else "Connected"
            self._session_start = time.time()
            self._session_title = title
            self._session_profile = profile
            self._session_bytes = (status.bytes_in, status.bytes_out)
            self._last_exit_ip = ""
            self.pages["connect"].set_state("connected", "Connected", title)
            self.session_card.update_state("connected", title, status.uptime)
            if status.local_ip:
                self.pages["connect"].set_exit_ip(status.local_ip, theme.GREEN)
            self.window.set_status("Connected - " + title, theme.GREEN)
            self.toast("Connected to " + title, "good")
            if self.store.data.kill_switch:
                self._arm_killswitch_async()
                self.window.after(HEALTH_DELAY, self._health_check)

        elif state == VpnState.FAILED:
            reason = status.last_error or "see logs"
            self._record_session("failed")
            self.pages["connect"].set_state("failed", "Failed", reason[:150])
            self.session_card.update_state("failed", profile.title if profile else "")
            self.window.set_status("Failed - " + reason[:60], theme.RED)
            if (self.store.data.auto_retry
                    and self._auto_retries < MAX_AUTO_RETRIES
                    and profile is not None
                    and self._pending is None):
                self._auto_retries += 1
                safe = self._auto_retries > SAFE_MODE_AFTER
                self.toast("Retrying %d/%d%s..." % (
                    self._auto_retries, MAX_AUTO_RETRIES,
                    " in safe mode" if safe else ""), "warn")
                self.window.after(2400,
                                  lambda p=profile, s=safe: self.connect_to(p, safe_mode=s))
            else:
                self._disarm_killswitch()
                self.toast("Connection failed", "bad")

        elif state == VpnState.DISCONNECTED:
            if self._connecting or self._pending is not None:
                target = (self._pending or (self.selected, False))[0]
                self.pages["connect"].set_state(
                    "connecting", "Switching", target.title if target else "")
                self.session_card.update_state("connecting",
                                               target.title if target else "")
            elif (not self._user_disconnect
                    and not self._closing
                    and self.store.data.reconnect_on_drop
                    and profile is not None
                    and self._drops < MAX_DROPS):
                self._drops += 1
                self.pages["connect"].set_state(
                    "connecting", "Tunnel dropped",
                    "reconnecting %d/%d" % (self._drops, MAX_DROPS))
                self.session_card.update_state("connecting",
                                               profile.title if profile else "")
                self.window.set_status("Tunnel dropped - reconnecting", theme.AMBER)
                self.toast("Tunnel dropped - reconnecting", "warn")
                self.window.after(DROP_DELAY, lambda p=profile: self.connect_to(p))
            else:
                self._record_session("ok")
                self.pages["connect"].set_state("idle", "Not connected",
                                                "Pick a server and hit connect")
                self.session_card.update_state("idle")
                self.pages["connect"].set_traffic(0, 0)
                self.pages["connect"].set_totals(0, 0)
                self.window.set_status("Disconnected", theme.TEXT_FAINT)
                self._disarm_killswitch()

        elif state.busy:
            label = state.value.replace("_", " ").title()
            detail = status.detail or (profile.title if profile else "")
            self.pages["connect"].set_state("connecting", label, detail)
            self.session_card.update_state("connecting", profile.title if profile else "")
            self.window.set_status(label + " - " + detail[:60], theme.AMBER)

    def _tick(self):
        if self._closing:
            return
        if self.session.status.is_up:
            uptime = self.session.status.uptime
            self._session_bytes = (self.session.status.bytes_in,
                                   self.session.status.bytes_out)
            self.pages["connect"].set_uptime(uptime)
            self.pages["connect"].set_totals(self.session.status.bytes_in,
                                             self.session.status.bytes_out)
            self.session_card.update_state(
                "connected",
                (self.session.status.profile.title
                 if self.session.status.profile else "Connected"),
                uptime)
        self.window.after(1000, self._tick)

    def shutdown(self):
        if self._closing:
            return
        self._closing = True
        if self.session.status.is_up:
            self._record_session("ok")
        try:
            self.session.shutdown()
        except Exception:
            pass
        if self.store.data.kill_switch:
            try:
                self.killswitch.clear()
            except Exception:
                pass
        try:
            self.store.update(window_geometry=self.window.geometry())
        except Exception:
            pass
        try:
            self.window.destroy()
        except Exception:
            pass


def run() -> int:
    enable_dpi_awareness()

    if not is_admin():
        import tkinter.messagebox as messagebox
        probe = tk.Tk()
        probe.withdraw()
        answer = messagebox.askyesno(
            "OxyVPN needs administrator rights",
            "OpenVPN, the kill switch and several scanner checks all need "
            "elevation.\n\nRelaunch OxyVPN as administrator?")
        probe.destroy()
        if answer and relaunch_elevated():
            return 0

    window = FramelessWindow()
    App(window)
    window.mainloop()
    return 0