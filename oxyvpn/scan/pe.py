"""Minimal PE (portable executable) header reader.

Pure stdlib. Reads only the header plus the section table, never the whole
image, so it stays fast across hundreds of files.
"""

from __future__ import annotations

import struct

from .util import entropy, read_head

HEAD_BYTES = 65536
MAX_SECTIONS = 24

INJECTION_IMPORTS = {
    "virtualalloc", "virtualallocex", "virtualprotect", "virtualprotectex",
    "writeprocessmemory", "readprocessmemory", "createremotethread",
    "createremotethreadex", "ntunmapviewofsection", "queueuserapc",
    "setthreadcontext", "resumethread", "shellexecutea", "shellexecutew",
    "winexec", "urldownloadtofilea", "urldownloadtofilew",
}

RECON_IMPORTS = {
    "isdebuggerpresent", "checkremotedebuggerpresent",
    "outputdebugstringa", "outputdebugstringw", "gettickcount",
    "queryperformancecounter", "sleep", "sleep_ex",
}

NETWORK_IMPORTS = {
    "internetopena", "internetopenw", "internetopenurla", "internetopenurlw",
    "httpopenrequesta", "httpopenrequestw", "httpsendrequesta",
    "httpsendrequestw", "wsastartup", "wsasocketa", "wsasocketw",
    "wsaconnect", "wsaconnectby", "send", "recv", "gethostbyname",
}

CRYPTO_IMPORTS = {
    "cryptacquirecontexta", "cryptacquirecontextw", "cryptencrypt",
    "cryptdecrypt", "cryptgenkey", "cryptcreatehash", "bcryptencrypt",
    "bcryptdecrypt",
}

SUSPICIOUS_SECTION_NAMES = {
    ".aspack", ".adata", ".mpress1", ".mpress2", ".themida", ".vmp0",
    ".vmp1", ".enigma1", ".enigma2", ".petite", ".upx0", ".upx1", ".perplex",
}


def parse(path):
    """Return a dict of header facts, or None when the file is not a PE."""
    head = read_head(path, HEAD_BYTES)
    if len(head) < 0x40 or head[:2] != b"MZ":
        return None
    try:
        e_lfanew = struct.unpack_from("<I", head, 0x3C)[0]
    except struct.error:
        return None
    if e_lfanew + 0x18 > len(head):
        return None
    if head[e_lfanew:e_lfanew + 4] != b"PE\0\0":
        return None

    coff = e_lfanew + 4
    try:
        machine, sections, timestamp, _, _, opt_size, _chars = \
            struct.unpack_from("<HHIIIHH", head, coff)
    except struct.error:
        return None

    optional = coff + 20
    if optional + opt_size > len(head):
        return None
    try:
        magic = struct.unpack_from("<H", head, optional)[0]
    except struct.error:
        return None
    pe32_plus = magic == 0x20B

    table = optional + opt_size
    parsed_sections = []
    for index in range(min(sections, MAX_SECTIONS)):
        offset = table + index * 40
        if offset + 40 > len(head):
            break
        name = head[offset:offset + 8].rstrip(b"\0").decode("latin-1", "ignore")
        try:
            vsize, vaddr, rawsize, rawptr = struct.unpack_from("<IIII", head, offset + 8)
            chars = struct.unpack_from("<I", head, offset + 36)[0]
        except struct.error:
            break
        parsed_sections.append({
            "name": name,
            "vsize": vsize,
            "vaddr": vaddr,
            "rawsize": rawsize,
            "rawptr": rawptr,
            "chars": chars,
        })

    cert_dir = optional + (112 if pe32_plus else 96) + 4 * 8
    cert_size = 0
    if cert_dir + 4 <= len(head):
        try:
            cert_size = struct.unpack_from("<I", head, cert_dir)[0]
        except struct.error:
            cert_size = 0

    return {
        "machine": machine,
        "sections": parsed_sections,
        "section_count": len(parsed_sections),
        "timestamp": timestamp,
        "opt_size": opt_size,
        "pe32_plus": pe32_plus,
        "signed": cert_size > 0,
        "imports": _imports(head, table, len(parsed_sections), sections),
        "overlay_hint": _overlay_hint(head, parsed_sections),
    }


def _imports(head, table, parsed_count, declared_count):
    """Crude name harvest from the import directory. Lowercase, deduped."""
    names = set()
    raw = head.lower()
    for token in (b"kernel32.dll", b"ntdll.dll", b"wininet.dll",
                  b"ws2_32.dll", b"advapi32.dll", b"user32.dll"):
        if token in raw:
            names.add(token.decode().replace(".dll", "_dll"))
    # Harvest ASCII identifiers that look like API names.
    for chunk in raw.split(b"\0"):
        if 4 <= len(chunk) <= 40:
            try:
                text = chunk.decode("ascii")
            except UnicodeDecodeError:
                continue
            if text.isalnum() or "_" in text:
                lowered = text.lower()
                if lowered in INJECTION_IMPORTS or lowered in NETWORK_IMPORTS:
                    names.add(lowered)
    return names


def _overlay_hint(head, sections):
    """True when there is meaningful data past the last raw section."""
    if not sections:
        return False
    end = max((s["rawptr"] + s["rawsize"]) for s in sections)
    return len(head) > end + 2048


def section_entropy(path, section):
    try:
        with open(path, "rb") as handle:
            handle.seek(section["rawptr"])
            data = handle.read(min(section["rawsize"], 262144))
    except OSError:
        return 0.0
    return entropy(data)


def packer_names(parsed):
    hits = set()
    for section in parsed.get("sections", []):
        name = section["name"].lower()
        if name in SUSPICIOUS_SECTION_NAMES:
            hits.add(name.lstrip("."))
    return sorted(hits)