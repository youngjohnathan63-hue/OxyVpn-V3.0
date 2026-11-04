"""Discovery and parsing of OpenVPN .ovpn profiles."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .audit import audit

REMOTE_RE = re.compile(r"^\s*remote\s+(\S+)(?:\s+(\d+))?", re.IGNORECASE | re.MULTILINE)
PROTO_RE = re.compile(r"^\s*proto\s+(\S+)", re.IGNORECASE | re.MULTILINE)
NAME_RE = re.compile(r"^([a-z]{2})[-_ ]?([a-z0-9#_\-]*)", re.IGNORECASE)

PINNED_PREFIX = ".oxyvpn-"

COUNTRY_NAMES = {
    "us": "United States", "nl": "Netherlands", "jp": "Japan", "pl": "Poland",
    "ro": "Romania", "de": "Germany", "fr": "France", "gb": "United Kingdom",
    "uk": "United Kingdom", "ca": "Canada", "ch": "Switzerland", "se": "Sweden",
    "no": "Norway", "dk": "Denmark", "fi": "Finland", "es": "Spain",
    "it": "Italy", "at": "Austria", "be": "Belgium", "ie": "Ireland",
    "pt": "Portugal", "cz": "Czechia", "hu": "Hungary", "sk": "Slovakia",
    "bg": "Bulgaria", "gr": "Greece", "au": "Australia", "sg": "Singapore",
    "hk": "Hong Kong", "in": "India", "br": "Brazil", "ar": "Argentina",
    "za": "South Africa", "il": "Israel", "tr": "Turkey", "ua": "Ukraine",
    "ee": "Estonia", "lv": "Latvia", "lt": "Lithuania", "is": "Iceland",
    "lu": "Luxembourg", "mx": "Mexico", "cl": "Chile", "co": "Colombia",
    "cr": "Costa Rica", "md": "Moldova", "rs": "Serbia", "hr": "Croatia",
    "si": "Slovenia", "tw": "Taiwan", "kr": "South Korea", "my": "Malaysia",
    "th": "Thailand", "nz": "New Zealand", "ae": "United Arab Emirates",
    "ng": "Nigeria", "ke": "Kenya", "eg": "Egypt", "ma": "Morocco",
    "tn": "Tunisia", "cy": "Cyprus", "mt": "Malta", "ge": "Georgia",
    "am": "Armenia", "kz": "Kazakhstan", "vn": "Vietnam", "ph": "Philippines",
    "id": "Indonesia", "pk": "Pakistan", "bd": "Bangladesh", "lk": "Sri Lanka",
}


@dataclass
class Profile:
    path: Path
    name: str
    host: str
    port: int
    proto: str
    country_code: str = ""
    country: str = ""
    city: str = ""
    tier: str = ""
    is_free: bool = False
    issues: list = field(default_factory=list)
    extras: dict = field(default_factory=dict)

    @property
    def title(self):
        if self.country and self.city:
            return "%s - %s" % (self.country, self.city)
        return self.country or self.country_code.upper() or self.name

    @property
    def subtitle(self):
        return "%s:%d  %s" % (self.host, self.port, self.proto.upper())

    @property
    def key(self):
        return str(self.path)


def _tidy_city(raw: str) -> str:
    text = raw.replace("#", "-").replace("_", "-")
    text = re.sub(r"-(udp|tcp|\d+)$", "", text, flags=re.IGNORECASE)
    text = text.strip("-")
    if text.lower() in ("free", "basic", "plus", "pro"):
        return text.title()
    return text.replace("-", " ").title()


def is_generated(path: Path) -> bool:
    return path.name.startswith(PINNED_PREFIX)


def parse_profile(path: Path):
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None

    remote = REMOTE_RE.search(text)
    if not remote:
        return None

    host = remote.group(1)
    port = int(remote.group(2)) if remote.group(2) else 1194
    proto_match = PROTO_RE.search(text)
    proto = proto_match.group(1).lower() if proto_match else "udp"

    stem = path.stem
    if stem.startswith(PINNED_PREFIX):
        stem = stem[len(PINNED_PREFIX):]
    base = stem.split(".")[0] or stem
    profile = Profile(path=path, name=base, host=host, port=port, proto=proto)

    match = NAME_RE.match(base)
    if match:
        code = match.group(1).lower()
        profile.country_code = code
        profile.country = COUNTRY_NAMES.get(code, code.upper())
        profile.city = _tidy_city(match.group(2))

    lowered = base.lower()
    profile.is_free = "free" in lowered
    for tier in ("free", "basic", "plus", "pro"):
        if tier in lowered:
            profile.tier = tier
            break

    profile.issues = audit(path)
    return profile


def scan_profiles(directory: Path):
    if not directory or not directory.is_dir():
        return []

    found = []
    seen = set()
    for path in sorted(directory.rglob("*.ovpn")):
        if is_generated(path):
            continue
        profile = parse_profile(path)
        if profile is None:
            continue
        fingerprint = (profile.host.lower(), profile.port, profile.proto)
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        found.append(profile)
    return found


def prune_generated(directory: Path) -> int:
    if not directory or not directory.is_dir():
        return 0
    removed = 0
    for path in directory.rglob(PINNED_PREFIX + "*.ovpn"):
        try:
            path.unlink()
            removed += 1
        except OSError:
            pass
    return removed