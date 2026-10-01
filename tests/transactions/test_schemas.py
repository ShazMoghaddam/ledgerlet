from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.modules.transactions.categories import TransactionCategory
from app.modules.transactions.schemas import TransactionCreate, TransactionUpdate

VALID = {
    "transaction_date": "2026-09-01",
    "category": "rental_income",
    "description": "September rent",
    "amount": "850.00",
}


def test_create_parses_types() -> None:
    data = TransactionCreate(**VALID)
    assert data.transaction_date == date(2026, 9, 1)
    assert data.category is TransactionCategory.RENTAL_INCOME
    assert data.amount == Decimal("850.00")


@pytest.mark.parametrize("amount", ["0", "-10", "1.005", "abc"])
def test_create_rejects_bad_amounts(amount: str) -> None:
    with pytest.raises(ValidationError):
        TransactionCreate(**{**VALID, "amount": amount})


def test_create_rejects_unknown_category() -> None:
    with pytest.raises(ValidationError):
        TransactionCreate(**{**VALID, "category": "mortgage_capital"})


def test_create_rejects_client_chosen_source() -> None:
    with pytest.raises(ValidationError):
        TransactionCreate(**{**VALID, "source": "open_banking"})


def test_update_tracks_only_sent_fields() -> None:
    assert TransactionUpdate(amount="10").model_dump(exclude_unset=True) == {
        "amount": Decimal("10")
    }


def test_update_rejects_null() -> None:
    with pytest.raises(ValidationError):
        TransactionUpdate(description=None)
