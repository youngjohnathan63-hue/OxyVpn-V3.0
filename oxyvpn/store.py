"""Persistent application settings stored as JSON in %APPDATA%."""

from __future__ import annotations

import base64
import json
import threading
from dataclasses import asdict, dataclass, field
from typing import Any

from .paths import SETTINGS_FILE, ensure_dirs


@dataclass
class Settings:
    openvpn_path: str = ""
    profiles_dir: str = ""
    username: str = ""
    password_b64: str = ""
    kill_switch: bool = True
    block_dns: bool = True
    block_ipv6: bool = True
    crypto_hardening: bool = True
    reconnect_on_drop: bool = True
    auto_retry: bool = True
    auto_connect: bool = False
    proto_mode: str = "auto"
    preferred_port: int = 0
    dns_override: str = ""
    retry_attempts: int = 3
    last_server: str = ""
    window_geometry: str = ""
    favorites: list = field(default_factory=list)
    sort_mode: str = "name"

    @property
    def password(self) -> str:
        if not self.password_b64:
            return ""
        try:
            return base64.b64decode(self.password_b64).decode("utf-8")
        except Exception:
            return ""

    @password.setter
    def password(self, value: str) -> None:
        self.password_b64 = base64.b64encode(
            (value or "").encode("utf-8")
        ).decode("ascii")


class SettingsStore:
    def __init__(self) -> None:
        ensure_dirs()
        self._lock = threading.RLock()
        self._data = self._load()

    def _load(self) -> Settings:
        if not SETTINGS_FILE.exists():
            return Settings()
        try:
            raw = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return Settings()
        known = set(Settings.__dataclass_fields__.keys())
        data = Settings(**{k: v for k, v in raw.items() if k in known})
        if not isinstance(data.favorites, list):
            data.favorites = []
        else:
            data.favorites = [str(k) for k in data.favorites]
        if data.sort_mode not in ("name", "latency", "favorites"):
            data.sort_mode = "name"
        if data.proto_mode not in ("auto", "udp", "tcp"):
            data.proto_mode = "auto"
        try:
            data.preferred_port = int(data.preferred_port or 0)
        except (TypeError, ValueError):
            data.preferred_port = 0
        if data.preferred_port < 0 or data.preferred_port > 65535:
            data.preferred_port = 0
        return data

    @property
    def data(self) -> Settings:
        return self._data

    def save(self) -> None:
        with self._lock:
            try:
                SETTINGS_FILE.write_text(
                    json.dumps(asdict(self._data), indent=2), encoding="utf-8"
                )
            except OSError:
                pass

    def update(self, **kwargs: Any) -> None:
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self._data, key):
                    setattr(self._data, key, value)
            self.save()