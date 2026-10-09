"""The transactions contract. Amounts travel as pounds (Decimal) over the API.

JSON clients may send "850.00" or 850. Responses always return a string such
as "850.00", which avoids floating-point surprises in browsers.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.transactions.categories import (
    TransactionCategory,
    TransactionKind,
    TransactionSource,
)

MAX_DIGITS = 12  # up to 9,999,999,999.99


class TransactionCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    transaction_date: date
    category: TransactionCategory
    description: str = Field(min_length=1, max_length=255, examples=["October rent"])
    amount: Decimal = Field(gt=0, max_digits=MAX_DIGITS, decimal_places=2, examples=["850.00"])


class TransactionUpdate(BaseModel):
    """Partial update (PATCH). The property a transaction belongs to can't be changed."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    transaction_date: date | None = None
    category: TransactionCategory | None = None
    description: str | None = Field(default=None, min_length=1, max_length=255)
    amount: Decimal | None = Field(default=None, gt=0, max_digits=MAX_DIGITS, decimal_places=2)

    @model_validator(mode="after")
    def _reject_nulls(self) -> Self:
        for name in self.model_fields_set:
            if getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        return self


class TransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    property_id: UUID
    transaction_date: date
    category: TransactionCategory
    kind: TransactionKind
    description: str
    amount: Decimal
    source: TransactionSource
    is_locked: bool
    locked_at: datetime | None
    created_at: datetime
    updated_at: datetime


class CategoryRead(BaseModel):
    value: TransactionCategory
    label: str
    kind: TransactionKind


class TransactionListItem(TransactionRead):
    """A row in the cross-property list, with the landlord's share already worked out.

    share_amount is for display. Tax totals are never built by adding these up:
    they apply the share per property per category, as the tax module does.
    """

    share_amount: Decimal


class TransactionPage(BaseModel):
    """One page of transactions, plus totals for everything that matches (not just this page).

    money_in and money_out are at the landlord's share. money_out includes
    mortgage interest, because it is money paid out, even though HMRC treats
    it separately from expenses.
    """

    items: list[TransactionListItem]
    total: int
    limit: int
    offset: int
    money_in: Decimal
    money_out: Decimal
