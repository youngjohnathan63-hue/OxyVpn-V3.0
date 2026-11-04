"""Subprocess, registry, hashing and PowerShell helpers."""

from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
import winreg

CREATE_NO_WINDOW = 0x08000000
HASH_CHUNK = 262144
MAX_HASH_BYTES = 96 * 1024 * 1024


def run(args, timeout=25):
    try:
        proc = subprocess.run(
            args, capture_output=True, text=True, timeout=timeout,
            creationflags=CREATE_NO_WINDOW, errors="ignore",
        )
    except Exception as exc:
        return 1, str(exc)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def powershell(script, timeout=60):
    return run(["powershell", "-NoProfile", "-NonInteractive",
                "-ExecutionPolicy", "Bypass", "-Command", script], timeout)[1]


def powershell_json(script, timeout=60):
    text = powershell(script, timeout).strip()
    if not text:
        return []
    try:
        data = json.loads(text)
    except Exception:
        return []
    if isinstance(data, dict):
        return [data]
    return data if isinstance(data, list) else []


def reg_read(hive, path, name, default=None):
    try:
        with winreg.OpenKey(hive, path) as key:
            value, _ = winreg.QueryValueEx(key, name)
            return value
    except OSError:
        return default


def reg_enum_values(hive, path):
    out = {}
    try:
        with winreg.OpenKey(hive, path) as key:
            index = 0
            while True:
                try:
                    name, value, _ = winreg.EnumValue(key, index)
                except OSError:
                    break
                out[name] = value
                index += 1
    except OSError:
        pass
    return out


def reg_enum_subkeys(hive, path):
    out = []
    try:
        with winreg.OpenKey(hive, path) as key:
            index = 0
            while True:
                try:
                    out.append(winreg.EnumKey(key, index))
                except OSError:
                    break
                index += 1
    except OSError:
        pass
    return out


def expand(path):
    try:
        return os.path.expandvars(path)
    except Exception:
        return path


def clean_path(raw):
    """Strip quotes and arguments from a registry command line."""
    if not raw:
        return ""
    text = raw.strip()
    if text.startswith('"'):
        end = text.find('"', 1)
        if end > 0:
            return text[1:end]
    if text.lower().endswith(".exe"):
        return text
    lowered = text.lower()
    marker = lowered.find(".exe")
    if marker > 0:
        return text[:marker + 4]
    return text.split(" ")[0]


def signature_map(paths):
    """Return {path: (status, signer)} via one batched PowerShell call."""
    paths = [p for p in dict.fromkeys(paths) if p and os.path.isfile(p)]
    if not paths:
        return {}
    joined = ",".join("'%s'" % p.replace("'", "''") for p in paths[:200])
    script = (
        "$out=@();"
        "foreach($p in @(%s)){"
        " $s=$null;"
        " try{ $s=Get-AuthenticodeSignature -LiteralPath $p -ErrorAction Stop }catch{};"
        " $out += [pscustomobject]@{"
        "  p=$p;"
        "  s=if($s){$s.Status.ToString()}else{'Unknown'};"
        "  n=if($s -and $s.SignerCertificate){$s.SignerCertificate.Subject}else{''}"
        " } }"
        ";$out|ConvertTo-Json -Compress"
    ) % joined
    rows = powershell_json(script, timeout=90)
    out = {}
    for row in rows:
        if isinstance(row, dict) and row.get("p"):
            out[row["p"]] = (row.get("s", "Unknown"), row.get("n", ""))
    return out


def read_head(path, size=4096):
    """Read the first bytes of a file, cheaply and safely."""
    try:
        with open(path, "rb") as handle:
            return handle.read(size)
    except (OSError, MemoryError):
        return b""


def sha256_file(path, cancel=None, limit=MAX_HASH_BYTES):
    """Hash a file. Returns (hexdigest, bytes_read) or ("", 0) on failure."""
    digest = hashlib.sha256()
    total = 0
    try:
        with open(path, "rb") as handle:
            while True:
                if cancel is not None and cancel.is_set():
                    return "", total
                if total >= limit:
                    break
                chunk = handle.read(HASH_CHUNK)
                if not chunk:
                    break
                digest.update(chunk)
                total += len(chunk)
    except (OSError, MemoryError):
        return "", total
    return digest.hexdigest(), total


def entropy(data):
    """Shannon entropy in bits per byte, 0.0 - 8.0."""
    if not data:
        return 0.0
    counts = [0] * 256
    for byte in data:
        counts[byte] += 1
    length = float(len(data))
    total = 0.0
    for count in counts:
        if not count:
            continue
        probability = count / length
        total -= probability * math.log2(probability)
    return total


def human_size(num):
    for unit in ("B", "KB", "MB", "GB"):
        if num < 1024:
            return "%.1f %s" % (num, unit)
        num /= 1024.0
    return "%.1f TB" % num