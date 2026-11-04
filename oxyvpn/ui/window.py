"""Frameless window: custom chrome, drag, resize and status strip."""

from __future__ import annotations

import ctypes
import re
import tkinter as tk

from . import branding, theme
from .widgets import round_rect

GWL_STYLE = -16
GWL_EXSTYLE = -20
WS_CAPTION = 0x00C00000
WS_SYSMENU = 0x00080000
WS_THICKFRAME = 0x00040000
WS_MINIMIZEBOX = 0x00020000
WS_MAXIMIZEBOX = 0x00010000
WS_EX_APPWINDOW = 0x00040000
WS_EX_TOOLWINDOW = 0x00000080
SPI_GETWORKAREA = 0x0030
SW_MINIMIZE = 6
SW_RESTORE = 9
GRIP = 5


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


class MARGINS(ctypes.Structure):
    _fields_ = [("cxLeftWidth", ctypes.c_int), ("cxRightWidth", ctypes.c_int),
                ("cyTopHeight", ctypes.c_int), ("cyBottomHeight", ctypes.c_int)]


def work_area():
    rect = RECT()
    try:
        ok = ctypes.windll.user32.SystemParametersInfoW(
            SPI_GETWORKAREA, 0, ctypes.byref(rect), 0)
        if ok:
            return rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top
    except Exception:
        pass
    return 0, 0, 1024, 700


def enable_dpi_awareness():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
        return
    except Exception:
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


class ChromeButton(tk.Canvas):
    """Caption button with a rounded hover plate and hairline glyph."""

    def __init__(self, master, kind, command, bg):
        super().__init__(master, width=46, height=46, bg=bg,
                         highlightthickness=0, bd=0, cursor="hand2")
        self.kind = kind
        self.command = command
        self._base = bg
        self._hover = False
        self.bind("<Button-1>", lambda e: self.command())
        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)
        self._draw()

    def _enter(self, _e):
        self._hover = True
        self._draw()

    def _leave(self, _e):
        self._hover = False
        self._draw()

    def _draw(self):
        self.delete("all")
        if self._hover:
            plate = theme.RED if self.kind == "close" else theme.SURFACE_HI
            round_rect(self, 5, 7, 41, 39, 7, plate, "")

        if self.kind == "close" and self._hover:
            colour = "#ffffff"
        elif self._hover:
            colour = theme.TEXT
        else:
            colour = theme.TEXT_MUTED

        cx, cy, arm = 23, 23, 5
        if self.kind == "min":
            self.create_line(cx - arm, cy, cx + arm, cy, fill=colour, width=1)
        elif self.kind == "max":
            round_rect(self, cx - arm, cy - arm, cx + arm, cy + arm, 2, "", colour, 1)
        elif self.kind == "restore":
            round_rect(self, cx - arm + 2, cy - arm, cx + arm, cy + arm - 2, 2,
                       "", colour, 1)
            round_rect(self, cx - arm, cy - arm + 2, cx + arm - 2, cy + arm, 2,
                       "", colour, 1)
        else:
            self.create_line(cx - arm, cy - arm, cx + arm, cy + arm,
                             fill=colour, width=1)
            self.create_line(cx + arm, cy - arm, cx - arm, cy + arm,
                             fill=colour, width=1)


class FramelessWindow(tk.Tk):
    def __init__(self, min_width=1080, min_height=700):
        super().__init__()

        work_x, work_y, work_w, work_h = work_area()
        self.min_width = min(min_width, work_w)
        self.min_height = min(min_height, work_h)

        self._maximised = False
        self._minimised = False
        self._restore_geometry = ""
        self._drag = {"x": 0, "y": 0}
        self._resize = {}
        self._taskbar_done = False

        self.overrideredirect(True)
        self.configure(bg=theme.BORDER)
        self.title("OxyVPN")

        width = max(self.min_width, min(1180, work_w - 40))
        height = max(self.min_height, min(760, work_h - 40))
        x = work_x + max(0, (work_w - width) // 2)
        y = work_y + max(0, (work_h - height) // 2)
        self.geometry("%dx%d+%d+%d" % (width, height, x, y))

        self._build_shell()
        self.bind("<Map>", self._on_map)
        self.after(40, self._fix_taskbar)

    # ------------------------------------------------------------- shell
    def _build_shell(self):
        self.shell = tk.Frame(self, bg=theme.BORDER)
        self.shell.pack(fill="both", expand=True)
        self.shell.rowconfigure(1, weight=1)
        self.shell.columnconfigure(1, weight=1)

        self.content = tk.Frame(self.shell, bg=theme.BG)
        self.content.grid(row=1, column=1, sticky="nsew")

        edges = {
            "n": (0, 1, "sb_h_double_arrow"), "s": (2, 1, "sb_h_double_arrow"),
            "w": (1, 0, "sb_v_double_arrow"), "e": (1, 2, "sb_v_double_arrow"),
            "nw": (0, 0, "size_nw_se"), "se": (2, 2, "size_nw_se"),
            "ne": (0, 2, "size_ne_sw"), "sw": (2, 0, "size_ne_sw"),
        }
        for edge, (row, col, cursor) in edges.items():
            grip = tk.Frame(self.shell, bg=theme.BORDER, cursor=cursor,
                            width=GRIP, height=GRIP)
            grip.grid(row=row, column=col, sticky="nsew")
            grip.grid_propagate(False)
            grip.bind("<ButtonPress-1>", lambda e, edge=edge: self._resize_start(edge))
            grip.bind("<B1-Motion>", self._resize_move)
            grip.bind("<ButtonRelease-1>", self._resize_end)

    def build_chrome(self, title, subtitle=""):
        self.titlebar = tk.Frame(self.content, bg=theme.BG_ALT, height=54)
        self.titlebar.pack(fill="x", side="top")
        self.titlebar.pack_propagate(False)
        tk.Frame(self.titlebar, bg=theme.HAIRLINE, height=1).pack(side="bottom", fill="x")

        left = tk.Frame(self.titlebar, bg=theme.BG_ALT)
        left.pack(side="left", fill="y")

        self.mark = tk.Canvas(left, width=26, height=26, bg=theme.BG_ALT,
                              highlightthickness=0, bd=0)
        self.mark.pack(side="left", padx=(16, 10), pady=14)
        branding.draw(self.mark, 13, 13, 26)

        tk.Label(left, text=title, bg=theme.BG_ALT, fg=theme.TEXT,
                 font=theme.f(theme.S11, "bold")).pack(side="left", pady=16)
        tk.Label(left, text=subtitle, bg=theme.SURFACE_HI, fg=theme.TEXT_MUTED,
                 font=theme.f(theme.S8, "bold"), padx=6, pady=1).pack(
            side="left", padx=(9, 0), pady=17)

        right = tk.Frame(self.titlebar, bg=theme.BG_ALT)
        right.pack(side="right", fill="y", padx=(0, 8))
        ChromeButton(right, "close", lambda: self.on_close(), theme.BG_ALT).pack(side="right")
        self._max_button = ChromeButton(right, "max", self.toggle_max, theme.BG_ALT)
        self._max_button.pack(side="right")
        ChromeButton(right, "min", self.iconify, theme.BG_ALT).pack(side="right")

        for widget in (self.titlebar, left):
            widget.bind("<ButtonPress-1>", self._drag_start)
            widget.bind("<B1-Motion>", self._drag_move)
            widget.bind("<Double-Button-1>", lambda e: self.toggle_max())
        return self.titlebar

    def build_statusbar(self):
        self.statusbar = tk.Frame(self.content, bg=theme.BG_ALT, height=30)
        self.statusbar.pack(fill="x", side="bottom")
        self.statusbar.pack_propagate(False)
        tk.Frame(self.statusbar, bg=theme.HAIRLINE, height=1).pack(side="top", fill="x")

        self.status_dot = tk.Canvas(self.statusbar, width=14, height=14,
                                    bg=theme.BG_ALT, highlightthickness=0, bd=0)
        self.status_dot.pack(side="left", padx=(16, 7))
        self._dot = self.status_dot.create_oval(4, 4, 10, 10,
                                                fill=theme.TEXT_FAINT,
                                                outline=theme.TEXT_FAINT)

        self.status_label = tk.Label(self.statusbar, text="Disconnected",
                                     bg=theme.BG_ALT, fg=theme.TEXT_FAINT,
                                     font=theme.f(theme.S9), anchor="w")
        self.status_label.pack(side="left")

        self.scan_label = tk.Label(self.statusbar, text="",
                                   bg=theme.BG_ALT, fg=theme.TEXT_FAINT,
                                   font=theme.m(theme.S8), anchor="e")
        self.scan_label.pack(side="right", padx=16)

        tk.Frame(self.statusbar, bg=theme.BORDER, width=1, height=12).pack(side="right")

        self.server_label = tk.Label(self.statusbar, text="",
                                     bg=theme.BG_ALT, fg=theme.TEXT_DIM,
                                     font=theme.m(theme.S8), anchor="e")
        self.server_label.pack(side="right", padx=16)

        return self.statusbar

    def set_status(self, text, colour):
        try:
            self.status_label.configure(text=text, fg=colour)
            self.status_dot.itemconfigure(self._dot, fill=colour, outline=colour)
        except tk.TclError:
            pass

    def set_status_extra(self, server="", scan=""):
        try:
            self.server_label.configure(text=server)
            self.scan_label.configure(text=scan)
        except tk.TclError:
            pass

    def apply_saved_geometry(self, geometry: str):
        match = re.match(r"^(\d+)x(\d+)([+-]\d+)([+-]\d+)$", (geometry or "").strip())
        if not match:
            return
        width, height, x, y = (int(p) for p in match.groups())
        work_x, work_y, work_w, work_h = work_area()
        width = max(self.min_width, min(width, work_w))
        height = max(self.min_height, min(height, work_h))
        x = max(work_x, min(x, work_x + work_w - width))
        y = max(work_y, min(y, work_y + work_h - height))
        self.geometry("%dx%d+%d+%d" % (width, height, x, y))

    # ------------------------------------------------------- win32 plumbing
    def _hwnd(self):
        return ctypes.windll.user32.GetParent(self.winfo_id()) or self.winfo_id()

    def _get_long(self, hwnd, index):
        getter = getattr(ctypes.windll.user32, "GetWindowLongPtrW", None) \
            or ctypes.windll.user32.GetWindowLongW
        return getter(hwnd, index)

    def _set_long(self, hwnd, index, value):
        setter = getattr(ctypes.windll.user32, "SetWindowLongPtrW", None) \
            or ctypes.windll.user32.SetWindowLongW
        setter(hwnd, index, value)

    def _apply_frame(self):
        """Give the borderless window a DWM shadow and rounded corners."""
        try:
            hwnd = self._hwnd()
            style = self._get_long(hwnd, GWL_STYLE)
            style |= (WS_CAPTION | WS_SYSMENU | WS_THICKFRAME
                      | WS_MINIMIZEBOX | WS_MAXIMIZEBOX)
            self._set_long(hwnd, GWL_STYLE, style)

            ex_style = self._get_long(hwnd, GWL_EXSTYLE)
            ex_style = (ex_style & ~WS_EX_TOOLWINDOW) | WS_EX_APPWINDOW
            self._set_long(hwnd, GWL_EXSTYLE, ex_style)

            margins = MARGINS(1, 1, 1, 1)
            ctypes.windll.dwmapi.DwmExtendFrameIntoClientArea(
                hwnd, ctypes.byref(margins))
        except Exception:
            pass

    def _fix_taskbar(self):
        if self._taskbar_done:
            return
        self._taskbar_done = True
        self._apply_frame()
        try:
            self.withdraw()
            self.after(15, self._remap)
        except Exception:
            pass

    def _remap(self):
        self.deiconify()
        self.lift()
        self.focus_force()

    def _on_map(self, _event=None):
        if not self._minimised:
            return
        self._minimised = False
        self._apply_frame()
        if not self._maximised:
            self.lift()
        self.focus_force()

    # ------------------------------------------------------------ dragging
    def _drag_start(self, event):
        self._drag = {"x": event.x_root - self.winfo_x(),
                      "y": event.y_root - self.winfo_y()}

    def _drag_move(self, event):
        if self._maximised:
            return
        self.geometry("+%d+%d" % (event.x_root - self._drag["x"],
                                  event.y_root - self._drag["y"]))

    # ------------------------------------------------------------ resizing
    def _resize_start(self, edge):
        self._resize = {"edge": edge, "px": self.winfo_pointerx(),
                        "py": self.winfo_pointery(), "w": self.winfo_width(),
                        "h": self.winfo_height(), "x": self.winfo_x(),
                        "y": self.winfo_y()}

    def _resize_move(self, _event):
        state = self._resize
        if not state:
            return
        dx = self.winfo_pointerx() - state["px"]
        dy = self.winfo_pointery() - state["py"]
        edge = state["edge"]
        width, height = state["w"], state["h"]
        x, y = state["x"], state["y"]
        if "e" in edge:
            width = max(self.min_width, state["w"] + dx)
        if "s" in edge:
            height = max(self.min_height, state["h"] + dy)
        if "w" in edge:
            width = max(self.min_width, state["w"] - dx)
            x = state["x"] + (state["w"] - width)
        if "n" in edge:
            height = max(self.min_height, state["h"] - dy)
            y = state["y"] + (state["h"] - height)
        self.geometry("%dx%d+%d+%d" % (width, height, x, y))

    def _resize_end(self, _event):
        self._resize = {}

    # --------------------------------------------------------- window state
    def iconify(self):
        """Minimise through Win32; Tk's iconify is a no-op when borderless."""
        try:
            ctypes.windll.user32.ShowWindow(self._hwnd(), SW_MINIMIZE)
            self._minimised = True
        except Exception:
            try:
                self.overrideredirect(False)
                self.iconify()
                self.after(60, lambda: self.overrideredirect(True))
            except Exception:
                pass

    def toggle_max(self):
        if self._maximised:
            self.geometry(self._restore_geometry or "1180x760")
            self._maximised = False
            self._max_button.kind = "max"
        else:
            self._restore_geometry = self.geometry()
            x, y, w, h = work_area()
            self.geometry("%dx%d+%d+%d" % (w, h, x, y))
            self._maximised = True
            self._max_button.kind = "restore"
        self._max_button._draw()

    def on_close(self):
        self.destroy()