from decimal import Decimal

import pytest

from app.core.money import from_pence, to_pence


@pytest.mark.parametrize(
    ("pounds", "pence"),
    [("0.01", 1), ("12.5", 1250), ("12.50", 1250), ("850", 85000), ("9999999999.99", 999999999999)],
)
def test_to_pence(pounds: str, pence: int) -> None:
    assert to_pence(Decimal(pounds)) == pence


def test_to_pence_refuses_fractions_of_a_penny() -> None:
    with pytest.raises(ValueError):
        to_pence(Decimal("1.005"))


@pytest.mark.parametrize(("pence", "pounds"), [(1, "0.01"), (1250, "12.50"), (85000, "850.00")])
def test_from_pence_always_two_places(pence: int, pounds: str) -> None:
    assert str(from_pence(pence)) == pounds


def test_round_trip_is_exact() -> None:
    for pence in (1, 99, 100, 123456, 10**11):
        assert to_pence(from_pence(pence)) == pence
