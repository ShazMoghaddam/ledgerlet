"""Money conversion between the API (pounds as Decimal) and storage (integer pence).

Storing integer pence makes rounding errors impossible: quarterly totals are
plain integer sums. Floats never touch money anywhere in LedgerLet.
"""

from decimal import Decimal

PENCE_PER_POUND = 100
_TWO_PLACES = Decimal("0.01")


def to_pence(amount: Decimal) -> int:
    """Decimal("12.50") -> 1250. Refuses anything finer than a penny."""
    pence = amount * PENCE_PER_POUND
    if pence != pence.to_integral_value():
        raise ValueError(f"{amount} has more than 2 decimal places")
    return int(pence)


def from_pence(pence: int) -> Decimal:
    """1250 -> Decimal("12.50")."""
    return (Decimal(pence) / PENCE_PER_POUND).quantize(_TWO_PLACES)
