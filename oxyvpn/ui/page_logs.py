"""Live log page with level filtering."""

from __future__ import annotations

import os
import re
import tkinter as tk
from tkinter import filedialog

from ..paths import OPENVPN_LOG
from . import theme
from .widgets import Chip, Eyebrow, FlatButton

LEVELS = [("All", ""), ("Errors", "bad"), ("Warnings", "warn"), ("Info", "good")]
MAX_LINES = 4000

# Order matters. A line is matched against each tier in turn and the first hit
# wins, so benign chatter is classified before the generic "fail" rule.
STRONG_BAD = re.compile(
    r"AUTH_FAILED|Options error|TLS Error|TLS handshake failed|"
    r"TLS key negotiation failed|cipher negotiation failed|"
    r"Cannot open TUN|Cannot open tap|All TAP-Windows adapters|"
    r"Exiting due to fatal error|fatal error|Inactivity timeout|"
    r"could not launch|was not found|not permitted|Access is denied",
    re.IGNORECASE)

BENIGN = re.compile(
    r"failed because route exists|route already exists|route exists|"
    r"OPTIONS IMPORT|OPTIONS IMPORT:|already exists|"
    r"NOTE:|Note: |Ignoring|DEPRECATED|preserving|"
    r"already disabled|already enabled|not required",
    re.IGNORECASE)

WARN = re.compile(
    r"WARNING|WARN|ipv6|retry|retrying|timeout|reconnecting|"
    r"deprecated|falling back|unable to|skipping|"
    r"may fail|may not work",
    re.IGNORECASE)

GENERIC_BAD = re.compile(r"\berror\b|\berrors\b|\bfailed\b|\bfailure\b|\bfail\b",
                         re.IGNORECASE)

GOOD = re.compile(
    r"Initialization Sequence Completed|CONNECTED,SUCCESS|"
    r"kill switch armed|armed:|disarmed|saved|Connected to|"
    r"adapter present|Detected",
    re.IGNORECASE)

MUTED = re.compile(r"^=====|^OpenVPN 2|^Library versions|^Originally developed by")


class LogsPage(tk.Frame):
    def __init__(self, master, app):
        super().__init__(master, bg=theme.BG)
        self.app = app
        self._buffer = []
        self._level = ""
        self.autoscroll = tk.BooleanVar(value=True)

        header = tk.Frame(self, bg=theme.BG)
        header.pack(fill="x", padx=28, pady=(18, 10))
        Eyebrow(header, "Diagnostics").pack(fill="x")
        tk.Label(header, text="Logs", bg=theme.BG, fg=theme.TEXT,
                 font=theme.f(theme.S28, "bold"), anchor="w").pack(fill="x", pady=(2, 0))

        tools = tk.Frame(self, bg=theme.BG)
        tools.pack(fill="x", padx=28, pady=(0, 10))

        self.chips = {}
        for label, tag in LEVELS:
            chip = Chip(tools, label, lambda t=tag: self._set_level(t))
            chip.pack(side="left", padx=(0, 6))
            self.chips[tag] = chip
        self.chips[""].set_selected(True)

        FlatButton(tools, "OpenVPN log", self._open_file,
                   kind="ghost").pack(side="right")
        FlatButton(tools, "Save", self._save, kind="ghost").pack(side="right", padx=8)
        FlatButton(tools, "Copy", self._copy, kind="ghost").pack(side="right")
        FlatButton(tools, "Clear", self._clear, kind="ghost").pack(side="right", padx=8)
        self.scroll_button = FlatButton(tools, "Autoscroll", self._toggle_autoscroll,
                                        kind="ghost")
        self.scroll_button.pack(side="right", padx=8)
        self._sync_autoscroll()

        shell = tk.Frame(self, bg=theme.BORDER)
        shell.pack(fill="both", expand=True, padx=28, pady=(0, 10))
        panel = tk.Frame(shell, bg=theme.BG_SUNKEN)
        panel.pack(fill="both", expand=True, padx=1, pady=1)

        self.text = tk.Text(panel, bg=theme.BG_SUNKEN, fg=theme.TEXT_DIM,
                            insertbackground=theme.TEXT, relief="flat",
                            font=theme.m(theme.S9), wrap="none", padx=16, pady=12,
                            selectbackground=theme.ACCENT_DIM, bd=0,
                            highlightthickness=0, spacing1=1, spacing3=2)
        scroll = tk.Scrollbar(panel, command=self.text.yview, bd=0, width=9,
                              bg=theme.SURFACE_HI, troughcolor=theme.BG_SUNKEN,
                              activebackground=theme.BORDER_HI, relief="flat")
        self.text.configure(yscrollcommand=scroll.set)
        self.text.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self.text.tag_configure("good", foreground=theme.GREEN)
        self.text.tag_configure("bad", foreground=theme.RED)
        self.text.tag_configure("warn", foreground=theme.AMBER)
        self.text.tag_configure("muted", foreground=theme.TEXT_FAINT)
        self.text.configure(state="disabled")

        self.footer = tk.Frame(self, bg=theme.BG)
        self.footer.pack(fill="x", padx=28, pady=(0, 16))
        self.counts = tk.Label(self.footer, text="", bg=theme.BG, fg=theme.TEXT_FAINT,
                               font=theme.m(theme.S8))
        self.counts.pack(side="left")
        tk.Label(self.footer, text="colours: error / warning / ok",
                 bg=theme.BG, fg=theme.TEXT_FAINT,
                 font=theme.f(theme.S8)).pack(side="right")
        self._update_counts()

    # ------------------------------------------------------------ classify
    def _tag_for(self, message: str):
        line = message.strip()
        if not line:
            return ""
        if STRONG_BAD.search(line):
            return "bad"
        if BENIGN.search(line):
            return ""
        if WARN.search(line):
            return "warn"
        if GENERIC_BAD.search(line):
            return "bad"
        if GOOD.search(line):
            return "good"
        if MUTED.search(line):
            return "muted"
        return ""

    # ------------------------------------------------------------ filtering
    def _set_level(self, tag):
        self._level = tag
        for key, chip in self.chips.items():
            chip.set_selected(key == tag)
        self._render()

    def _toggle_autoscroll(self):
        self.autoscroll.set(not self.autoscroll.get())
        self._sync_autoscroll()

    def _sync_autoscroll(self):
        self.scroll_button.configure(
            fg=theme.ACCENT if self.autoscroll.get() else theme.TEXT_DIM)

    def _render(self):
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        for tag, message in self._buffer:
            if self._level and tag != self._level:
                continue
            self.text.insert("end", message + "\n", tag)
        if self.autoscroll.get():
            self.text.see("end")
        self.text.configure(state="disabled")
        self._update_counts()

    def _update_counts(self):
        errors = sum(1 for tag, _ in self._buffer if tag == "bad")
        warnings = sum(1 for tag, _ in self._buffer if tag == "warn")
        self.counts.configure(
            text="%d lines  ·  %d errors  ·  %d warnings"
                 % (len(self._buffer), errors, warnings))

    # ---------------------------------------------------------------- input
    def append(self, message: str):
        tag = self._tag_for(message)
        self._buffer.append((tag, message))
        if len(self._buffer) > MAX_LINES:
            del self._buffer[:500]
            self._render()
            return
        if self._level and tag != self._level:
            self._update_counts()
            return
        try:
            self.text.configure(state="normal")
            self.text.insert("end", message + "\n", tag)
            if self.autoscroll.get():
                self.text.see("end")
            self.text.configure(state="disabled")
            self._update_counts()
        except tk.TclError:
            pass

    # -------------------------------------------------------------- actions
    def _clear(self):
        self._buffer = []
        self._render()

    def _copy(self):
        try:
            self.clipboard_clear()
            self.clipboard_append("\n".join(m for _, m in self._buffer))
            self.app.toast("Log copied", "good")
        except tk.TclError:
            pass

    def _save(self):
        path = filedialog.asksaveasfilename(defaultextension=".log",
                                            initialfile="oxyvpn.log")
        if path:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("\n".join(m for _, m in self._buffer))

    def _open_file(self):
        if OPENVPN_LOG.exists():
            os.startfile(str(OPENVPN_LOG))