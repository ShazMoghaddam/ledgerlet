"""The parser is pure: these tests need no database and no app."""

from datetime import date
from decimal import Decimal

import pytest

from app.modules.imports.parser import CsvFormatError, Direction, parse_statement
from app.modules.imports.schemas import CsvMapping

SIGNED = CsvMapping(date_column="Date", description_column="Description", amount_column="Amount")
SPLIT = CsvMapping(
    date_column="Date",
    description_column="Details",
    paid_in_column="Paid in",
    paid_out_column="Paid out",
    date_format="%Y-%m-%d",
)


def csv_bytes(*lines: str, encoding: str = "utf-8") -> bytes:
    return ("\n".join(lines) + "\n").encode(encoding)


def test_signed_amounts_set_direction() -> None:
    rows = parse_statement(
        csv_bytes("Date,Description,Amount", "01/09/2026,RENT,850.00", "02/09/2026,B&Q,-45.99"),
        SIGNED,
    )
    assert [(r.direction, r.amount) for r in rows] == [
        (Direction.IN, Decimal("850.00")),
        (Direction.OUT, Decimal("45.99")),
    ]
    assert rows[0].transaction_date == date(2026, 9, 1)


def test_pound_signs_commas_and_brackets() -> None:
    rows = parse_statement(
        csv_bytes("Date,Description,Amount", '01/09/2026,A,"£1,250.00"', "01/09/2026,B,(12.50)"),
        SIGNED,
    )
    assert rows[0].amount == Decimal("1250.00")
    assert (rows[1].direction, rows[1].amount) == (Direction.OUT, Decimal("12.50"))


def test_invert_sign_for_exports_where_spending_is_positive() -> None:
    mapping = SIGNED.model_copy(update={"invert_sign": True})
    rows = parse_statement(csv_bytes("Date,Description,Amount", "01/09/2026,CARD,25.00"), mapping)
    assert rows[0].direction is Direction.OUT


def test_split_paid_in_and_out_columns() -> None:
    rows = parse_statement(
        csv_bytes(
            "Date,Details,Paid in,Paid out",
            "2026-09-01,RENT,850.00,",
            "2026-09-02,AGENT,,85.00",
            "2026-09-03,BOTH,1,2",
            "2026-09-04,NEITHER,,",
        ),
        SPLIT,
    )
    assert [r.direction for r in rows[:2]] == [Direction.IN, Direction.OUT]
    assert [r.is_valid for r in rows] == [True, True, False, False]


def test_bad_rows_are_reported_not_fatal() -> None:
    rows = parse_statement(
        csv_bytes(
            "Date,Description,Amount",
            "31/02/2026,BAD DATE,10",
            "01/09/2026,ZERO,0",
            "01/09/2026,WORDS,ten",
            "01/09/2026,PRECISE,1.005",
            "01/09/2026,FINE,10",
        ),
        SIGNED,
    )
    assert [r.is_valid for r in rows] == [False, False, False, False, True]
    assert all(r.error for r in rows[:4])


def test_line_numbers_match_the_file_and_blank_lines_are_skipped() -> None:
    rows = parse_statement(
        csv_bytes("Date,Description,Amount", "01/09/2026,A,1", "", "02/09/2026,B,2"), SIGNED
    )
    assert [r.line for r in rows] == [2, 4]


def test_headers_match_case_insensitively() -> None:
    rows = parse_statement(csv_bytes(" DATE ,description,AMOUNT", "01/09/2026,A,1"), SIGNED)
    assert rows[0].is_valid


def test_description_whitespace_is_collapsed() -> None:
    content = csv_bytes("Date,Description,Amount", "01/09/2026,  J   SMITH ,1")
    rows = parse_statement(content, SIGNED)
    assert rows[0].description == "J SMITH"


def test_excel_bom_and_old_windows_encoding() -> None:
    bom = "\ufeffDate,Description,Amount\n01/09/2026,A,1\n".encode()
    assert parse_statement(bom, SIGNED)[0].is_valid
    cp1252 = csv_bytes("Date,Description,Amount", "01/09/2026,Café £,1", encoding="cp1252")
    assert parse_statement(cp1252, SIGNED)[0].description == "Café £"


def test_missing_column_is_a_file_error() -> None:
    with pytest.raises(CsvFormatError, match="Description"):
        parse_statement(csv_bytes("Date,Memo,Amount", "01/09/2026,A,1"), SIGNED)


def test_empty_file_is_a_file_error() -> None:
    with pytest.raises(CsvFormatError):
        parse_statement(b"", SIGNED)
