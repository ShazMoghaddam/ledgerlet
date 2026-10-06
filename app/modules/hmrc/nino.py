"""National Insurance numbers: validation and masking. Pure functions.

Format: two prefix letters, six digits, suffix A to D (e.g. QQ123456C).
D, F, I, Q, U and V never appear in the prefix; O never appears second; and some
pairs are never issued (BG, GB, KN, NK, NT, TN, ZZ).
"""

import re

_PATTERN = re.compile(r"^(?!BG|GB|KN|NK|NT|TN|ZZ)[A-CEGHJ-PR-TW-Z][A-CEGHJ-NPR-TW-Z]\d{6}[A-D]$")


def normalise_nino(raw: str) -> str:
    """'oe 18 06 77 a' -> 'OE180677A'. Raises ValueError if it isn't a valid NINO."""
    compact = re.sub(r"\s+", "", raw).upper()
    if not _PATTERN.match(compact):
        raise ValueError("That isn't a valid National Insurance number")
    return compact


def mask_nino(nino: str) -> str:
    """'OE180677A' -> 'OE****77A'. Enough to recognise, not enough to use."""
    return f"{nino[:2]}****{nino[6:]}"
