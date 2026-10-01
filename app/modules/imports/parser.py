"""Pure CSV statement parsing: bytes in, rows out. No database, no HTTP.

One bad row never sinks the file: it comes back with an error message so the
landlord can see it. Only problems with the file as a whole (unreadable, a
mapped column missing) raise CsvFormatError.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import TYPE_CHECKING

from app.core.exceptions import BusinessRuleError

if TYPE_CHECKING:
    from app.modules.imports.schemas import CsvMapping

MAX_DESCRIPTION_LENGTH = 255
MAX_AMOUNT = Decimal("9999999999.99")
_PENNY = Decimal("0.01")


class Direction(StrEnum):
    IN = "in"
    OUT = "out"


class CsvFormatError(BusinessRuleError):
    """The file as a whole can't be read with this mapping."""


@dataclass(frozen=True)
class ParsedRow:
    line: int
    transaction_date: date | None
    description: str
    amount: Decimal | None  # always positive; direction says which way
    direction: Direction | None
    error: str | None = None

    @property
    def is_valid(self) -> bool:
        return self.error is None


def parse_statement(content: bytes, mapping: CsvMapping) -> list[ParsedRow]:
    reader = csv.DictReader(io.StringIO(_decode(content)))
    if not reader.fieldnames:
        raise CsvFormatError("The file is empty or has no header row")

    # Match mapped column names case-insensitively, ignoring stray spaces.
    available = {name.strip().lower(): name for name in reader.fieldnames if name}

    def resolve(wanted: str | None) -> str | None:
        if wanted is None:
            return None
        actual = available.get(wanted.strip().lower())
        if actual is None:
            found = ", ".join(n.strip() for n in reader.fieldnames or [] if n)
            raise CsvFormatError(f"Column '{wanted}' not found. Columns in this file: {found}")
        return actual

    date_col = resolve(mapping.date_column)
    desc_col = resolve(mapping.description_column)
    amount_col = resolve(mapping.amount_column)
    in_col = resolve(mapping.paid_in_column)
    out_col = resolve(mapping.paid_out_column)

    rows: list[ParsedRow] = []
    for record in reader:
        if not any(isinstance(v, str) and v.strip() for v in record.values()):
            continue  # blank line
        description = _clean_description(record.get(desc_col or ""))
        try:
            tx_date = _parse_date(record.get(date_col or ""), mapping.date_format)
            if amount_col is not None:
                amount, direction = _from_signed(record.get(amount_col), mapping.invert_sign)
            else:
                amount, direction = _from_split(record.get(in_col or ""), record.get(out_col or ""))
        except ValueError as exc:
            rows.append(ParsedRow(reader.line_num, None, description, None, None, error=str(exc)))
            continue
        rows.append(ParsedRow(reader.line_num, tx_date, description, amount, direction))
    return rows


def _decode(content: bytes) -> str:
    # utf-8-sig strips the byte-order mark Excel adds; cp1252 covers older
    # UK exports where "£" isn't UTF-8.
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise CsvFormatError("Couldn't read the file. Please export it as CSV (UTF-8).")


def _clean_description(raw: str | None) -> str:
    cleaned = " ".join((raw or "").split())
    return cleaned[:MAX_DESCRIPTION_LENGTH] or "(no description)"


def _parse_date(raw: str | None, date_format: str) -> date:
    value = (raw or "").strip()
    if not value:
        raise ValueError("Missing date")
    try:
        return datetime.strptime(value, date_format).date()
    except ValueError:
        raise ValueError(f"Date '{value}' doesn't match the format {date_format}") from None


def _parse_money(raw: str | None) -> Decimal | None:
    """'£1,250.00' -> 1250.00, '(12.50)' -> -12.50, '' -> None."""
    value = (raw or "").strip()
    if not value:
        return None
    negative = value.startswith("(") and value.endswith(")")
    cleaned = value.strip("()").replace("£", "").replace(",", "").replace(" ", "")
    try:
        amount = Decimal(cleaned)
    except InvalidOperation:
        raise ValueError(f"Amount '{value}' isn't a number") from None
    if not amount.is_finite():
        raise ValueError(f"Amount '{value}' isn't a number")
    if amount != amount.quantize(_PENNY):
        raise ValueError(f"Amount '{value}' has more than 2 decimal places")
    if abs(amount) > MAX_AMOUNT:
        raise ValueError(f"Amount '{value}' is too large")
    return -amount if negative else amount


def _from_signed(raw: str | None, invert: bool) -> tuple[Decimal, Direction]:
    amount = _parse_money(raw)
    if amount is None:
        raise ValueError("Missing amount")
    if invert:
        amount = -amount
    if amount == 0:
        raise ValueError("Amount is zero")
    return abs(amount), Direction.IN if amount > 0 else Direction.OUT


def _from_split(raw_in: str | None, raw_out: str | None) -> tuple[Decimal, Direction]:
    paid_in = _parse_money(raw_in) or None  # treat 0 like blank
    paid_out = _parse_money(raw_out) or None
    if paid_in is None and paid_out is None:
        raise ValueError("No amount in either the paid in or paid out column")
    if paid_in is not None and paid_out is not None:
        raise ValueError("Both paid in and paid out are filled")
    if paid_in is not None:
        return abs(paid_in), Direction.IN
    assert paid_out is not None
    return abs(paid_out), Direction.OUT
