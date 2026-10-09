"""Money conversion between the API (pounds as Decimal) and storage (integer pence).

Storing integer pence makes rounding errors impossible: quarterly totals are
plain integer sums. Floats never touch money anywhere in LedgerLet.
"""

from decimal import ROUND_HALF_UP, Decimal

PENCE_PER_POUND = 100
_TWO_PLACES = Decimal("0.01")
_WHOLE_PENNY = Decimal("1")


def to_pence(amount: Decimal) -> int:
    """Decimal("12.50") -> 1250. Refuses anything finer than a penny."""
    pence = amount * PENCE_PER_POUND
    if pence != pence.to_integral_value():
        raise ValueError(f"{amount} has more than 2 decimal places")
    return int(pence)


def from_pence(pence: int) -> Decimal:
    """1250 -> Decimal("12.50")."""
    return (Decimal(pence) / PENCE_PER_POUND).quantize(_TWO_PLACES)


def share_of(amount_pence: int, ownership_percentage: Decimal) -> int:
    """An owner's share of an amount, rounded half up to the penny.

    50% of 101p is 50.5p, which rounds to 51p. Lives here, not in the tax module,
    because transactions also shows each row's share.
    """
    exact = Decimal(amount_pence) * ownership_percentage / 100
    return int(exact.quantize(_WHOLE_PENNY, rounding=ROUND_HALF_UP))
