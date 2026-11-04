"""Static heuristics over a parsed PE image."""

from __future__ import annotations

from . import pe

HIGH_ENTROPY = 7.2
VERY_HIGH_ENTROPY = 7.6
WRITABLE_EXEC = 0x20000000  # IMAGE_SCN_MEM_EXECUTE
WRITABLE = 0x80000000       # IMAGE_SCN_MEM_WRITE


def evaluate(path, parsed):
    """Return a list of (weight, rule_id, message) tuples. Higher = worse."""
    hits = []
    if parsed is None:
        return hits

    sections = parsed["sections"]
    if not sections:
        hits.append((2, "PE_NOSEC", "PE image declares no sections"))

    worst = 0.0
    worst_name = ""
    for section in sections:
        score = pe.section_entropy(path, section)
        if score > worst:
            worst, worst_name = score, section["name"] or "?"

    if worst >= VERY_HIGH_ENTROPY:
        hits.append((4, "PE_PACKED",
                     "Section %s is %.2f bits/byte - almost certainly packed or encrypted"
                     % (worst_name, worst)))
    elif worst >= HIGH_ENTROPY:
        hits.append((2, "PE_ENTROPY",
                     "Section %s is %.2f bits/byte - compressed or packed"
                     % (worst_name, worst)))

    for section in sections:
        if section["chars"] & WRITABLE and section["chars"] & WRITABLE_EXEC:
            hits.append((3, "PE_WX",
                         "Section %s is writable and executable at once"
                         % (section["name"] or "?")))
            break

    packers = pe.packer_names(parsed)
    if packers:
        hits.append((3, "PE_PACKERNAME",
                     "Section names match a known packer: %s"
                     % ", ".join(packers)))

    imports = parsed["imports"]
    injection = imports & pe.INJECTION_IMPORTS
    if len(injection) >= 3:
        hits.append((4, "PE_INJECT",
                     "Import table carries injection primitives: %s"
                     % ", ".join(sorted(injection)[:5])))
    if imports & pe.RECON_IMPORTS and injection:
        hits.append((2, "PE_EVASION",
                     "Combines debugger checks with injection imports"))
    if len(imports & pe.NETWORK_IMPORTS) >= 2 and injection:
        hits.append((3, "PE_DOWNLOADER",
                     "Injection plus network imports - downloader shape"))
    if len(imports & pe.CRYPTO_IMPORTS) >= 2 and injection:
        hits.append((2, "PE_CRYPTO",
                     "Injection plus crypto imports - possible packer/ransomware"))

    if parsed["overlay_hint"]:
        hits.append((2, "PE_OVERLAY",
                     "Large data overlay appended past the last section"))

    if parsed["section_count"] <= 2 and worst >= HIGH_ENTROPY:
        hits.append((2, "PE_TINY_PACKED",
                     "Only %d section(s) and packed - typical crypter output"
                     % parsed["section_count"]))

    if not parsed["signed"]:
        hits.append((1, "PE_NOSIG", "No embedded Authenticode certificate"))

    return hits


def total_weight(hits):
    return sum(weight for weight, _, _ in hits)