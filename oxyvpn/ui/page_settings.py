"""Settings page."""

from __future__ import annotations

import platform
import threading
import tkinter as tk
from tkinter import filedialog

from .. import __version__
from ..netinfo import lookup_public_ip
from ..vpn.locate import adapter_present, find_openvpn, version_of
from . import theme
from .widgets import Card, Chip, Eyebrow, FlatButton, ScrollFrame, ToggleSwitch

PROTO_CHOICES = [("Auto", "auto"), ("UDP", "udp"), ("TCP", "tcp")]


class Field(tk.Frame):
    def __init__(self, master, label, value, browse=None, secret=False):
        super().__init__(master, bg=theme.SURFACE)
        tk.Label(self, text=label.upper(), bg=theme.SURFACE, fg=theme.TEXT_FAINT,
                 font=theme.f(theme.S8, "bold"), anchor="w").pack(fill="x", pady=(0, 5))
        row = tk.Frame(self, bg=theme.SURFACE)
        row.pack(fill="x")
        self.var = tk.StringVar(value=value)
        entry = tk.Entry(row, textvariable=self.var, show="*" if secret else "",
                         bg=theme.BG_SUNKEN, fg=theme.TEXT, insertbackground=theme.TEXT,
                         relief="flat", font=theme.f(theme.S9), bd=0,
                         highlightthickness=1, highlightbackground=theme.BORDER,
                         highlightcolor=theme.ACCENT)
        entry.pack(side="left", fill="x", expand=True, ipady=6, ipadx=8)
        entry.bind("<FocusIn>", lambda e: entry.configure(
            highlightbackground=theme.ACCENT))
        entry.bind("<FocusOut>", lambda e: entry.configure(
            highlightbackground=theme.BORDER))
        if browse:
            FlatButton(row, "Browse", browse, kind="ghost").pack(side="right", padx=(8, 0))


class SettingsPage(tk.Frame):
    def __init__(self, master, app):
        super().__init__(master, bg=theme.BG)
        self.app = app
        settings = app.store.data

        header = tk.Frame(self, bg=theme.BG)
        header.pack(fill="x", padx=28, pady=(18, 12))
        Eyebrow(header, "Configuration").pack(fill="x")
        tk.Label(header, text="Settings", bg=theme.BG, fg=theme.TEXT,
                 font=theme.f(theme.S28, "bold"), anchor="w").pack(fill="x", pady=(2, 0))

        actions = tk.Frame(self, bg=theme.BG)
        actions.pack(fill="x", side="bottom", padx=28, pady=(10, 18))
        tk.Frame(actions, bg=theme.HAIRLINE, height=1).pack(fill="x", pady=(0, 12))
        FlatButton(actions, "Save settings", self._save, kind="accent").pack(side="left")
        FlatButton(actions, "Check exit IP", self._check_ip,
                   kind="ghost").pack(side="left", padx=8)
        FlatButton(actions, "Copy diagnostics", self._diagnostics,
                   kind="ghost").pack(side="left")
        FlatButton(actions, "Clean pinned copies", self._prune,
                   kind="ghost").pack(side="left", padx=8)
        self.status = tk.Label(actions, text="", bg=theme.BG, fg=theme.TEXT_FAINT,
                               font=theme.f(theme.S9), anchor="e")
        self.status.pack(side="right")

        body = ScrollFrame(self, bg=theme.BG)
        body.pack(fill="both", expand=True, padx=28, pady=(0, 4))
        column = body.inner

        openvpn_card = Card(column, title="OpenVPN engine",
                            subtitle="Path to openvpn.exe. Auto-detect checks the "
                                     "usual install locations.")
        openvpn_card.pack(fill="x", pady=(0, 12))
        self.openvpn_field = Field(openvpn_card.body, "openvpn.exe path",
                                   settings.openvpn_path, self._browse_openvpn)
        self.openvpn_field.pack(fill="x", pady=(2, 8))
        self.detect_label = tk.Label(openvpn_card.body, text="", bg=theme.SURFACE,
                                     fg=theme.TEXT_FAINT, font=theme.m(theme.S8),
                                     anchor="w", justify="left")
        self.detect_label.pack(fill="x")
        FlatButton(openvpn_card.body, "Auto-detect", self._detect,
                   kind="ghost").pack(anchor="w", pady=(8, 0))

        conn_card = Card(column, title="Connection",
                         subtitle="TCP 443 gets through most captive portals and "
                                  "blocked-UDP networks.")
        conn_card.pack(fill="x", pady=(0, 12))
        chips = tk.Frame(conn_card.body, bg=theme.SURFACE)
        chips.pack(fill="x", pady=(2, 8))
        self.proto_chips = {}
        for label, mode in PROTO_CHOICES:
            chip = Chip(chips, label, lambda m=mode: self._set_proto(m),
                        bg=theme.SURFACE)
            chip.pack(side="left", padx=(0, 6))
            self.proto_chips[mode] = chip
        self.proto_chips.get(settings.proto_mode,
                             self.proto_chips["auto"]).set_selected(True)

        self.port_field = Field(conn_card.body, "override port (0 = keep profile)",
                                str(settings.preferred_port or ""))
        self.port_field.pack(fill="x", pady=(0, 8))

        self.dns_field = Field(conn_card.body, "dns override (blank = profile default)",
                               settings.dns_override)
        self.dns_field.pack(fill="x")

        profiles_card = Card(column, title="Profiles",
                             subtitle="Folder scanned recursively for .ovpn files.")
        profiles_card.pack(fill="x", pady=(0, 12))
        self.profiles_field = Field(profiles_card.body, "folder containing .ovpn files",
                                    settings.profiles_dir, self._browse_profiles)
        self.profiles_field.pack(fill="x", pady=(2, 0))

        creds_card = Card(column, title="Credentials",
                          subtitle="account.protonvpn.com > Account > OpenVPN / IKEv2 username")
        creds_card.pack(fill="x", pady=(0, 12))
        self.user_field = Field(creds_card.body, "username", settings.username)
        self.user_field.pack(fill="x", pady=(2, 8))
        self.pass_field = Field(creds_card.body, "password", settings.password, secret=True)
        self.pass_field.pack(fill="x")

        security = Card(column, title="Security",
                        subtitle="Saved the moment you flip them.")
        security.pack(fill="x", pady=(0, 12))
        self.kill_var = tk.BooleanVar(value=settings.kill_switch)
        self.dns_var = tk.BooleanVar(value=settings.block_dns)
        self.ipv6_var = tk.BooleanVar(value=settings.block_ipv6)
        self.crypto_var = tk.BooleanVar(value=settings.crypto_hardening)
        self._toggle_row(security.body, "Kill switch", "kill_switch",
                         "Block all non-VPN traffic from the moment a handshake "
                         "starts until the tunnel closes", self.kill_var)
        self._toggle_row(security.body, "DNS leak protection", "block_dns",
                         "Force all name resolution through the tunnel", self.dns_var)
        self._toggle_row(security.body, "IPv6 leak protection", "block_ipv6",
                         "Block IPv6 outside the tunnel so v6 traffic cannot "
                         "bypass it", self.ipv6_var)
        self._toggle_row(security.body, "Strict crypto", "crypto_hardening",
                         "TLS 1.2+, forward-secret ciphers, AES-GCM / ChaCha20",
                         self.crypto_var)

        behaviour = Card(column, title="Behaviour",
                         subtitle="Saved the moment you flip them.")
        behaviour.pack(fill="x", pady=(0, 4))
        self.retry_var = tk.BooleanVar(value=settings.auto_retry)
        self.reconnect_var = tk.BooleanVar(value=settings.reconnect_on_drop)
        self.autostart_var = tk.BooleanVar(value=settings.auto_connect)
        self._toggle_row(behaviour.body, "Auto-retry", "auto_retry",
                         "Re-attempt a failed handshake automatically", self.retry_var)
        self._toggle_row(behaviour.body, "Reconnect on drop", "reconnect_on_drop",
                         "Rebuild the tunnel if it drops unexpectedly",
                         self.reconnect_var)
        self._toggle_row(behaviour.body, "Connect on launch", "auto_connect",
                         "Open the tunnel to the last used server at startup",
                         self.autostart_var)

        self.refresh()

    def _toggle_row(self, master, title, key, subtitle, variable):
        row = tk.Frame(master, bg=theme.SURFACE)
        row.pack(fill="x", pady=7)
        text = tk.Frame(row, bg=theme.SURFACE)
        text.pack(side="left", fill="x", expand=True)
        tk.Label(text, text=title, bg=theme.SURFACE, fg=theme.TEXT,
                 font=theme.f(theme.S10), anchor="w").pack(fill="x")
        tk.Label(text, text=subtitle, bg=theme.SURFACE, fg=theme.TEXT_FAINT,
                 font=theme.f(theme.S8), anchor="w", justify="left",
                 wraplength=440).pack(fill="x")
        switch = ToggleSwitch(row, variable, bg=theme.SURFACE,
                              command=lambda k=key, v=variable: self._persist(k, v))
        switch.pack(side="right", padx=(12, 0))

    def _persist(self, key, variable):
        try:
            self.app.store.update(**{key: bool(variable.get())})
            self._flash("Saved")
        except Exception:
            self._flash("Could not save", theme.RED)

    def _set_proto(self, mode):
        for key, chip in self.proto_chips.items():
            chip.set_selected(key == mode)
        self.app.store.update(proto_mode=mode)
        self._flash("Saved")

    def _flash(self, text, colour=theme.GREEN):
        self.status.configure(text=text, fg=colour)
        job = getattr(self, "_flash_job", None)
        if job is not None:
            try:
                self.after_cancel(job)
            except Exception:
                pass
        self._flash_job = self.after(
            2200, lambda: self.status.configure(text="", fg=theme.TEXT_FAINT))

    def refresh(self):
        path = find_openvpn(self.app.store.data.openvpn_path)
        if not path:
            self.detect_label.configure(
                text="openvpn.exe not found. Install OpenVPN or point at the binary.",
                fg=theme.AMBER)
            return
        has_adapter = adapter_present()
        self.detect_label.configure(
            text="Found: %s\n%s\n%s" % (path, version_of(path) or "unknown version",
                                        "adapter present" if has_adapter
                                        else "no TAP/Wintun adapter yet"),
            fg=theme.GREEN if has_adapter else theme.AMBER)

    def _browse_openvpn(self):
        path = filedialog.askopenfilename(
            title="Select openvpn.exe",
            filetypes=[("OpenVPN executable", "openvpn.exe"), ("Executables", "*.exe")])
        if path:
            self.openvpn_field.var.set(path)

    def _browse_profiles(self):
        path = filedialog.askdirectory(title="Select the folder with .ovpn files")
        if path:
            self.profiles_field.var.set(path)

    def _detect(self):
        found = find_openvpn("")
        if found:
            self.openvpn_field.var.set(found)
            self.status.configure(text="Detected", fg=theme.GREEN)
        else:
            self.status.configure(text="Not found on this system.", fg=theme.AMBER)
        self.refresh()

    def _prune(self):
        removed = self.app.prune_pinned()
        self.status.configure(text="Removed %d pinned copies" % removed, fg=theme.GREEN)

    def _diagnostics(self):
        lines = [
            "OxyVPN diagnostics",
            "version   : %s" % __version__,
            "python    : %s" % platform.python_version(),
            "os        : %s" % platform.platform(),
            "elevated  : %s" % bool(self.app.window and True),
            "openvpn   : %s" % (find_openvpn(self.app.store.data.openvpn_path) or "not found"),
            "adapter   : %s" % ("present" if adapter_present() else "missing"),
            "profiles  : %d (%d with warnings)"
                        % (len(self.app.profiles),
                           sum(1 for p in self.app.profiles if p.issues)),
            "proto     : %s  port: %s  dns: %s"
                        % (self.app.store.data.proto_mode,
                           self.app.store.data.preferred_port or "profile",
                           self.app.store.data.dns_override or "profile"),
            "state     : %s" % self.app.session.status.state.value,
            "",
            "recent log:",
        ]
        lines += [m for _, m in self.app.pages["logs"]._buffer[-15:]]
        try:
            self.clipboard_clear()
            self.clipboard_append("\n".join(lines))
            self._flash("Diagnostics copied")
        except tk.TclError:
            self._flash("Could not copy", theme.RED)

    def _read_port(self):
        try:
            value = int(self.port_field.var.get().strip() or 0)
        except ValueError:
            return 0
        return value if 0 <= value <= 65535 else 0

    def _save(self):
        self.app.store.update(
            openvpn_path=self.openvpn_field.var.get().strip(),
            profiles_dir=self.profiles_field.var.get().strip(),
            username=self.user_field.var.get().strip(),
            preferred_port=self._read_port(),
            dns_override=self.dns_field.var.get().strip(),
            kill_switch=self.kill_var.get(),
            block_dns=self.dns_var.get(),
            block_ipv6=self.ipv6_var.get(),
            crypto_hardening=self.crypto_var.get(),
            auto_retry=self.retry_var.get(),
            reconnect_on_drop=self.reconnect_var.get(),
            auto_connect=self.autostart_var.get(),
        )
        self.app.store.data.password = self.pass_field.var.get()
        self.app.store.save()
        self.app.reload_profiles()
        self.status.configure(text="Settings saved.", fg=theme.GREEN)

    def _check_ip(self):
        self.status.configure(text="Checking...", fg=theme.TEXT_FAINT)

        def worker():
            info = lookup_public_ip()

            def show():
                if info.ok:
                    self.status.configure(
                        text="Exit IP: %s  %s %s" % (info.ip, info.city, info.country),
                        fg=theme.GREEN)
                    self.app.pages["connect"].set_exit_ip(info.ip, theme.GREEN)
                else:
                    self.status.configure(text="Lookup failed: " + info.error,
                                          fg=theme.RED)
            self.app.post(show)

        threading.Thread(target=worker, daemon=True).start()

    def _clear_killswitch(self):
        self.app.killswitch.clear()
        self.status.configure(text="Kill-switch rules removed.", fg=theme.GREEN)