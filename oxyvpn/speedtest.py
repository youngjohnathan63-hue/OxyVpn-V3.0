"""Throughput measurement against Cloudflare's public speed endpoint."""

from __future__ import annotations

import time
import urllib.request

DOWN_URL = "https://speed.cloudflare.com/__down?bytes=%d"
UP_URL = "https://speed.cloudflare.com/__up"
USER_AGENT = "OxyVPN/2.1"
CHUNK = 65536
ATTEMPTS = 2


def download(total_bytes=6000000, timeout=15.0, on_progress=None,
             should_stop=None) -> float:
    """Megabits per second, or -1 on failure."""
    for _ in range(ATTEMPTS):
        if should_stop and should_stop():
            return -1.0
        result = _download_once(total_bytes, timeout, on_progress, should_stop)
        if result >= 0:
            return result
    return -1.0


def _download_once(total_bytes, timeout, on_progress, should_stop) -> float:
    request = urllib.request.Request(
        DOWN_URL % total_bytes,
        headers={"User-Agent": USER_AGENT,
                 "Accept-Encoding": "identity",
                 "Cache-Control": "no-store",
                 "Connection": "keep-alive"})

    start = time.perf_counter()
    received = 0
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            while True:
                if should_stop and should_stop():
                    return -1.0
                chunk = response.read(CHUNK)
                if not chunk:
                    break
                received += len(chunk)
                if on_progress:
                    elapsed = max(time.perf_counter() - start, 0.001)
                    on_progress(received, total_bytes,
                                received * 8.0 / elapsed / 1000000.0)
    except Exception:
        return -1.0

    elapsed = time.perf_counter() - start
    if received < 65536 or elapsed <= 0:
        return -1.0
    return received * 8.0 / elapsed / 1000000.0


def upload(payload_bytes=2000000, timeout=25.0, should_stop=None) -> float:
    """Megabits per second, or -1 on failure."""
    if should_stop and should_stop():
        return -1.0

    payload = b"\0" * payload_bytes
    request = urllib.request.Request(
        UP_URL, data=payload, method="POST",
        headers={"User-Agent": USER_AGENT,
                 "Accept-Encoding": "identity",
                 "Content-Type": "application/octet-stream",
                 "Content-Length": str(payload_bytes)})

    start = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response.read()
    except Exception:
        return -1.0

    elapsed = time.perf_counter() - start
    if elapsed <= 0:
        return -1.0
    return payload_bytes * 8.0 / elapsed / 1000000.0