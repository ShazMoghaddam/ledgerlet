"""Pure, dependency-free helpers. Easy to test, reusable anywhere."""

import re

# Official UK postcode shape (outward code + inward code), checked without spaces.
_UK_POSTCODE = re.compile(
    r"^(GIR0AA|"
    r"[A-PR-UWYZ]([0-9]{1,2}|[A-HK-Y][0-9]{1,2}|[0-9][A-HJKPS-UW]|[A-HK-Y][0-9][ABEHMNPRV-Y])"
    r"[0-9][ABD-HJLNP-UW-Z]{2})$"
)


def normalise_uk_postcode(raw: str) -> str:
    """Return a postcode in canonical form ("sw1a1aa" -> "SW1A 1AA").

    Raises ValueError if it isn't a valid UK postcode shape.
    """
    compact = re.sub(r"\s+", "", raw).upper()
    if not _UK_POSTCODE.match(compact):
        raise ValueError(f"'{raw}' is not a valid UK postcode")
    return f"{compact[:-3]} {compact[-3:]}"
