"""Completed session history, appended to JSONL in %APPDATA%."""

from __future__ import annotations

import json
import threading

from ..paths import APP_DIR

HISTORY_FILE = APP_DIR / "history.jsonl"
MAX_ENTRIES = 500

_lock = threading.Lock()


def record(entry: dict) -> None:
    with _lock:
        try:
            APP_DIR.mkdir(parents=True, exist_ok=True)
            with HISTORY_FILE.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(entry) + "\n")
        except OSError:
            pass


def load(limit: int = MAX_ENTRIES) -> list:
    if not HISTORY_FILE.exists():
        return []
    entries = []
    try:
        for line in HISTORY_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except ValueError:
                continue
    except OSError:
        return []
    return entries[-limit:][::-1]


def clear() -> None:
    with _lock:
        try:
            if HISTORY_FILE.exists():
                HISTORY_FILE.unlink()
        except OSError:
            pass


def totals(entries) -> dict:
    count = len(entries)
    seconds = sum(float(e.get("seconds") or 0) for e in entries)
    down = sum(int(e.get("down") or 0) for e in entries)
    up = sum(int(e.get("up") or 0) for e in entries)
    ok = sum(1 for e in entries if e.get("outcome") == "ok")
    return {"count": count, "seconds": seconds, "down": down, "up": up,
            "ok": ok, "rate": (ok / float(count) * 100.0) if count else 0.0}