"""File-content checks: hashing, reputation, PE structure, script bodies."""

from __future__ import annotations

import os
import re
import threading

from . import hashdb, heuristics, pe
from .models import Finding, Severity, Status
from .util import human_size, sha256_file

CANCEL = threading.Event()

MAX_FILES = 320
MAX_FILE_BYTES = 96 * 1024 * 1024
SCRIPT_EXTS = (".ps1", ".vbs", ".vbe", ".js", ".jse", ".wsf", ".hta", ".bat", ".cmd")
BINARY_EXTS = (".exe", ".dll", ".scr", ".com", ".pif", ".sys", ".ocx")

RISKY_ROOTS = [
    os.environ.get("TEMP", ""),
    os.environ.get("TMP", ""),
    r"C:\Windows\Temp",
    os.environ.get("LOCALAPPDATA", ""),
    os.path.join(os.environ.get("USERPROFILE", ""), "Downloads"),
    os.path.join(os.environ.get("USERPROFILE", ""), "AppData", "Roaming"),
]

SCRIPT_PATTERNS = [
    ("SC_ENCODED", 3, re.compile(r"-e(nc(odedcommand)?)?\s+[A-Za-z0-9+/=]{40,}",
                                 re.IGNORECASE),
     "Base64 -EncodedCommand blob"),
    ("SC_B64", 2, re.compile(r"frombase64string", re.IGNORECASE),
     "Base64 decode call"),
    ("SC_DOWNLOAD", 3, re.compile(r"(downloadstring|downloadfile|urlcache|"
                                  r"xmldocument|urldownloadtofile)", re.IGNORECASE),
     "Remote payload download"),
    ("SC_EXEC", 2, re.compile(r"(invoke-expression|iex\b|wscript\.shell|"
                              r"shell\.application|createobject)", re.IGNORECASE),
     "Shell execution"),
    ("SC_HIDDEN", 2, re.compile(r"(-w(indowstyle)?\s+hidden|-nop\b|bypass)",
                                re.IGNORECASE),
     "Hidden / policy-bypass flags"),
    ("SC_PERSIST", 2, re.compile(r"(currentversion\\run|schtasks|register-scheduledtask)",
                                 re.IGNORECASE),
     "Persistence registration"),
    ("SC_AMSI", 2, re.compile(r"amsiutils|amsiinitfailed", re.IGNORECASE),
     "AMSI bypass"),
]


def _candidates():
    """Collect executable and script files from the risky roots."""
    seen = set()
    out = []
    for root in RISKY_ROOTS:
        if not root or not os.path.isdir(root):
            continue
        try:
            for entry in os.scandir(root):
                if CANCEL.is_set() or len(out) >= MAX_FILES:
                    return out
                if not entry.is_file():
                    continue
                lowered = entry.name.lower()
                if not lowered.endswith(BINARY_EXTS + SCRIPT_EXTS):
                    continue
                key = entry.path.lower()
                if key in seen:
                    continue
                seen.add(key)
                out.append(entry.path)
        except OSError:
            continue
    return out


def _finding(check_id, title, severity, status, summary, path="", **extra):
    return Finding(check_id, title, "Binaries", severity, status, summary,
                   extra.pop("details", []), extra.pop("remediation", ""),
                   extra.pop("evidence", ""), path,
                   extra.pop("sha256", ""), extra.pop("entropy", 0.0))


def check_hash_reputation():
    """Hash every candidate and compare against the offline list."""
    files = _candidates()
    if not files:
        return _finding("BIN001", "File reputation", Severity.INFO, Status.INFO,
                        "No candidate files to hash")

    table = hashdb.load()
    matches = []
    hashed = 0
    for path in files:
        if CANCEL.is_set():
            break
        try:
            if os.path.getsize(path) > MAX_FILE_BYTES:
                continue
        except OSError:
            continue
        digest, _size = sha256_file(path, CANCEL)
        if not digest:
            continue
        hashed += 1
        hit = hashdb.lookup(digest, table)
        if hit:
            matches.append((path, digest, hit))

    if matches:
        details = ["%s  [%s - %s]" % (p, h[0], h[1]) for p, _d, h in matches[:20]]
        first_path, first_digest, first_hit = matches[0]
        return _finding(
            "BIN001", "Known-bad file hash", Severity.CRITICAL, Status.FAIL,
            "%d file(s) matched the known-bad hash list" % len(matches),
            path=first_path, sha256=first_digest, details=details,
            remediation="Quarantine or delete the matched files, then re-scan.",
            evidence="%s -> %s" % (first_path, first_hit[0]))
    return _finding("BIN001", "File reputation", Severity.INFO, Status.PASS,
                    "%d file(s) hashed, no known-bad matches" % hashed)


def check_pe_structure():
    """Parse PE headers and score them with the static heuristics."""
    files = [p for p in _candidates() if p.lower().endswith(BINARY_EXTS)]
    if not files:
        return _finding("BIN002", "Binary structure", Severity.INFO, Status.INFO,
                        "No PE files in the risky folders")

    suspicious = []
    parsed_count = 0
    for path in files:
        if CANCEL.is_set():
            break
        parsed = pe.parse(path)
        if parsed is None:
            continue
        parsed_count += 1
        hits = heuristics.evaluate(path, parsed)
        weight = heuristics.total_weight(hits)
        if weight >= 6:
            suspicious.append((weight, path, hits, parsed))

    if not suspicious:
        return _finding("BIN002", "Binary structure", Severity.INFO, Status.PASS,
                        "%d PE file(s) parsed, none look packed or injected"
                        % parsed_count)

    suspicious.sort(key=lambda row: row[0], reverse=True)
    details = []
    for weight, path, hits, _parsed in suspicious[:12]:
        top = sorted(hits, key=lambda h: h[0], reverse=True)[:2]
        details.append("%s (weight %d)" % (path, weight))
        for _w, _rule, message in top:
            details.append("    . %s" % message)

    worst_weight, worst_path, worst_hits, worst_parsed = suspicious[0]
    digest, _size = sha256_file(worst_path, CANCEL)
    severity = Severity.HIGH if worst_weight >= 10 else Severity.MEDIUM
    return _finding(
        "BIN002", "Packed or injected binaries", severity, Status.WARN,
        "%d binary(ies) show packing/injection traits" % len(suspicious),
        path=worst_path, sha256=digest,
        details=details,
        remediation="Anything you do not recognise here is worth uploading to "
                    "a multi-engine scanner for a second opinion.",
        evidence="\n".join("%s -> %s" % (p, m) for _w, p, h, _p2 in
                           suspicious[:3] for _w2, _r, m in h[:1]))


def check_script_bodies():
    """Read script files and look for dropper / persistence patterns."""
    files = [p for p in _candidates() if p.lower().endswith(SCRIPT_EXTS)]
    if not files:
        return _finding("BIN003", "Script bodies", Severity.INFO, Status.INFO,
                        "No scripts in the risky folders")

    flagged = []
    for path in files:
        if CANCEL.is_set():
            break
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as handle:
                text = handle.read(400000)
        except OSError:
            continue
        matched = [(rule, weight, message)
                   for rule, weight, pattern, message in SCRIPT_PATTERNS
                   if pattern.search(text)]
        if not matched:
            continue
        score = sum(weight for _r, weight, _m in matched)
        if score >= 4:
            flagged.append((score, path, matched))

    if not flagged:
        return _finding("BIN003", "Script bodies", Severity.INFO, Status.PASS,
                        "%d script(s) read, none look like droppers" % len(files))

    flagged.sort(key=lambda row: row[0], reverse=True)
    details = []
    for _score, path, matched in flagged[:10]:
        details.append(path)
        details.extend("    . %s" % message for _r, _w, message in matched)
    worst_score, worst_path, _m = flagged[0]
    severity = Severity.HIGH if worst_score >= 8 else Severity.MEDIUM
    return _finding(
        "BIN003", "Suspicious script content", severity, Status.WARN,
        "%d script(s) match dropper patterns" % len(flagged),
        path=worst_path, details=details,
        remediation="Open the file in Notepad - these patterns are readable.")


def check_unsigned_binaries():
    """Unsigned PE files sitting in staging folders."""
    from .util import signature_map
    files = [p for p in _candidates() if p.lower().endswith(BINARY_EXTS)]
    if not files:
        return _finding("BIN004", "Signature coverage", Severity.INFO, Status.INFO,
                        "No binaries to verify")

    sigs = signature_map(files[:120])
    unsigned = []
    for path in files:
        status, signer = sigs.get(path, ("", ""))
        if status in ("NotSigned", "HashMismatch", "NotTrusted"):
            unsigned.append("%s (%s)" % (path, status))
        elif status == "" and not path.lower().endswith(".dll"):
            unsigned.append("%s (unverified)" % path)

    if not unsigned:
        return _finding("BIN004", "Signature coverage", Severity.INFO, Status.PASS,
                        "All %d binary(ies) carry a trusted signature" % len(files))
    severity = Severity.MEDIUM if len(unsigned) > 6 else Severity.LOW
    return _finding(
        "BIN004", "Unsigned binaries in staging folders", severity, Status.WARN,
        "%d unsigned or untrusted binary(ies)" % len(unsigned),
        details=unsigned[:20],
        remediation="Loose unsigned executables in Temp or Downloads are the "
                    "single most common malware location.")


def check_large_entropy_files():
    """Files of any type with near-maximum entropy in the risky folders."""
    files = [p for p in _candidates() if p.lower().endswith(BINARY_EXTS)]
    if not files:
        return _finding("BIN005", "Entropy sweep", Severity.INFO, Status.INFO,
                        "Nothing to measure")
    from .util import entropy, read_head
    hot = []
    for path in files:
        if CANCEL.is_set():
            break
        try:
            size = os.path.getsize(path)
        except OSError:
            continue
        if size < 16384:
            continue
        score = entropy(read_head(path, 131072))
        if score >= 7.5:
            hot.append("%s - %.2f bits/byte, %s" % (path, score, human_size(size)))
    if not hot:
        return _finding("BIN005", "Entropy sweep", Severity.INFO, Status.PASS,
                        "No near-maximum entropy binaries")
    return _finding(
        "BIN005", "Encrypted / packed payloads", Severity.MEDIUM, Status.WARN,
        "%d file(s) are close to random data" % len(hot), details=hot[:15],
        remediation="Expect this for installers and updaters - investigate the "
                    "ones you did not download.")


CHECKS = [
    ("BIN001", "Hash reputation", check_hash_reputation),
    ("BIN002", "Binary structure", check_pe_structure),
    ("BIN003", "Script bodies", check_script_bodies),
    ("BIN004", "Signature coverage", check_unsigned_binaries),
    ("BIN005", "Entropy sweep", check_large_entropy_files),
]