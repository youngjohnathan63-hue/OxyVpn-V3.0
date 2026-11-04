"""Static hygiene checks for .ovpn files."""

from __future__ import annotations

import re
from pathlib import Path

LEGACY_CIPHERS = ("bf-cbc", "des-cbc", "des-ede3-cbc", "rc2-cbc", "none")
WEAK_DIGESTS = ("sha1", "md5")


def audit(path: Path) -> list:
    """Return human readable problems. Empty list means the file looks sane."""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ["unreadable file"]

    lowered = text.lower()
    issues = []

    if not re.search(r"(?im)^\s*remote\s+\S+", text):
        issues.append("no remote directive")
    if not re.search(r"(?im)^\s*dev\s+", text):
        issues.append("no dev directive")
    if not re.search(r"(?im)^\s*ca\s+", text) and "<ca>" not in lowered:
        issues.append("no CA certificate")

    for cipher in LEGACY_CIPHERS:
        if re.search(r"(?im)^\s*cipher\s+" + re.escape(cipher) + r"\s*$", text):
            issues.append("legacy cipher %s" % cipher.upper())
            break

    for digest in WEAK_DIGESTS:
        if re.search(r"(?im)^\s*auth\s+" + re.escape(digest) + r"\s*$", text):
            issues.append("weak auth %s" % digest.upper())
            break

    if not re.search(r"(?im)^\s*tls-(auth|crypt)\s+", text) and "<tls-" not in lowered:
        issues.append("no TLS auth key")

    if re.search(r"(?im)^\s*comp-lzo\s", text):
        issues.append("comp-lzo enabled")

    return issues