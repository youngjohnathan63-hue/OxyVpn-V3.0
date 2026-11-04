"""Offline known-bad hash list plus optional online reputation lookup."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

SEED = {
    # EICAR anti-malware test file - the canonical self-test.
    "275a021bbfb6489e54d471899f7db9d1663fc695ec2fe2a2c4538aabf651fd0f":
        ("EICAR test file", "test"),
    # WannaCry / WCry dropper.
    "24d004a104d4d54034dbcffc2a4b19a11f39008a575aa614ea04703480b1022c":
        ("WannaCry ransomware", "ransomware"),
}

ONLINE_ENDPOINT = "https://mb-api.abuse.ch/api/v1/"
USER_AGENT = "OxyVPN-Scanner/1.0"


def _data_dir():
    """Local storage for the user-editable hash list. Created on demand."""
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    path = os.path.join(base, "OxyVPN")
    try:
        os.makedirs(path, exist_ok=True)
    except OSError:
        pass
    return path


def _db_path():
    return os.path.join(_data_dir(), "hashdb.txt")


def load():
    """Return {sha256: (label, kind)}. User file augments the seed list."""
    table = dict(SEED)
    path = _db_path()
    if not os.path.isfile(path):
        return table
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as handle:
            for line in handle:
                line = line.split("#", 1)[0].strip()
                if not line:
                    continue
                parts = line.split(None, 2)
                if not parts:
                    continue
                digest = parts[0].lower()
                if len(digest) != 64:
                    continue
                label = parts[1] if len(parts) > 1 else "known-bad"
                kind = parts[2] if len(parts) > 2 else "malware"
                table[digest] = (label, kind)
    except OSError:
        pass
    return table


def lookup(digest, table=None):
    table = table if table is not None else load()
    return table.get((digest or "").lower())


def lookup_online(digest, timeout=6):
    """Query MalwareBazaar. Returns (label, kind) or None. Network required."""
    if not digest:
        return None
    body = urllib.parse.urlencode(
        {"query": "get_info", "hash": digest}).encode()
    request = urllib.request.Request(
        ONLINE_ENDPOINT, data=body, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8", "ignore"))
    except (urllib.error.URLError, ValueError, OSError):
        return None
    if payload.get("query_status") != "ok":
        return None
    rows = payload.get("data") or []
    if not rows:
        return None
    row = rows[0]
    signature = row.get("signature") or row.get("file_type") or "known-bad"
    return (signature, "tagged" if row.get("tags") else "malware")