"""A stable identity for a bank row, so the same statement can't be imported twice.

Banks don't give rows ids, so we hash what identifies the row: date, direction,
amount and description. Two identical rows in one file (two 10.00 payments to
the same shop on the same day) are told apart by an occurrence number, which
stays the same if the file is imported again.
"""

import hashlib
from collections import Counter
from datetime import date

from app.modules.imports.parser import Direction


def normalise_description(description: str) -> str:
    return " ".join(description.upper().split())


def fingerprint(
    transaction_date: date,
    direction: Direction,
    amount_pence: int,
    description: str,
    occurrence: int,
) -> str:
    key = "|".join(
        [
            transaction_date.isoformat(),
            direction.value,
            str(amount_pence),
            normalise_description(description),
            str(occurrence),
        ]
    )
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


class FingerprintCounter:
    """Hands out fingerprints for rows in file order, numbering identical rows 1, 2, 3..."""

    def __init__(self) -> None:
        self._seen: Counter[tuple[date, Direction, int, str]] = Counter()

    def next(
        self, transaction_date: date, direction: Direction, amount_pence: int, description: str
    ) -> str:
        base = (transaction_date, direction, amount_pence, normalise_description(description))
        self._seen[base] += 1
        return fingerprint(transaction_date, direction, amount_pence, description, self._seen[base])
