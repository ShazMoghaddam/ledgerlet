from datetime import date

from app.modules.imports.fingerprint import FingerprintCounter, fingerprint
from app.modules.imports.parser import Direction

DAY = date(2026, 9, 1)


def test_fingerprint_is_stable_and_hex() -> None:
    a = fingerprint(DAY, Direction.IN, 85000, "J SMITH RENT", 1)
    assert a == fingerprint(DAY, Direction.IN, 85000, "J SMITH RENT", 1)
    assert len(a) == 64


def test_description_case_and_spacing_dont_matter() -> None:
    assert fingerprint(DAY, Direction.IN, 1, "j  smith", 1) == fingerprint(
        DAY, Direction.IN, 1, "J SMITH", 1
    )


def test_every_field_matters() -> None:
    base = fingerprint(DAY, Direction.IN, 100, "X", 1)
    assert base != fingerprint(date(2026, 9, 2), Direction.IN, 100, "X", 1)
    assert base != fingerprint(DAY, Direction.OUT, 100, "X", 1)
    assert base != fingerprint(DAY, Direction.IN, 101, "X", 1)
    assert base != fingerprint(DAY, Direction.IN, 100, "Y", 1)


def test_identical_rows_in_one_file_get_distinct_but_repeatable_fingerprints() -> None:
    first_import = FingerprintCounter()
    a1 = first_import.next(DAY, Direction.OUT, 1000, "TESCO")
    a2 = first_import.next(DAY, Direction.OUT, 1000, "TESCO")

    second_import = FingerprintCounter()
    b1 = second_import.next(DAY, Direction.OUT, 1000, "tesco")
    b2 = second_import.next(DAY, Direction.OUT, 1000, "tesco")

    assert a1 != a2
    assert (a1, a2) == (b1, b2)
