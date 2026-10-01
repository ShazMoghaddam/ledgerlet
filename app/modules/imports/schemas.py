"""The imports contract: how to read the CSV, what the preview shows, what confirm accepts."""

from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.imports.parser import Direction
from app.modules.transactions.categories import TransactionCategory, TransactionKind

DEFAULT_DATE_FORMAT = "%d/%m/%Y"  # UK banks: 01/09/2026
MAX_ROWS = 5000


class CsvMapping(BaseModel):
    """Which columns hold what. Amounts are either one signed column, or paid in + paid out."""

    model_config = ConfigDict(str_strip_whitespace=True)

    date_column: str = Field(min_length=1, examples=["Date"])
    description_column: str = Field(min_length=1, examples=["Description"])
    amount_column: str | None = Field(default=None, examples=["Amount"])
    paid_in_column: str | None = None
    paid_out_column: str | None = None
    date_format: str = DEFAULT_DATE_FORMAT
    invert_sign: bool = False  # for exports where money out is positive

    @field_validator("amount_column", "paid_in_column", "paid_out_column", mode="before")
    @classmethod
    def _blank_is_none(cls, value: object) -> object:
        return None if isinstance(value, str) and not value.strip() else value

    @field_validator("date_format")
    @classmethod
    def _looks_like_a_format(cls, value: str) -> str:
        if "%" not in value:
            raise ValueError("date_format must be a pattern such as %d/%m/%Y")
        return value

    @model_validator(mode="after")
    def _one_amount_style(self) -> Self:
        signed = self.amount_column is not None
        split_in, split_out = self.paid_in_column is not None, self.paid_out_column is not None
        if signed and (split_in or split_out):
            raise ValueError("Use either amount_column or paid in/out columns, not both")
        if not signed and not (split_in and split_out):
            raise ValueError("Give amount_column, or both paid_in_column and paid_out_column")
        return self


class RowStatus(StrEnum):
    NEW = "new"
    ALREADY_IMPORTED = "already_imported"  # exact match: will be skipped on confirm
    POSSIBLE_DUPLICATE = "possible_duplicate"  # same date and amount exists: landlord decides
    INVALID = "invalid"


class PreviewRow(BaseModel):
    line: int
    status: RowStatus
    message: str | None
    transaction_date: date | None
    description: str
    amount: Decimal | None
    direction: Direction | None
    suggested_kind: TransactionKind | None
    fingerprint: str | None


class ImportPreview(BaseModel):
    property_id: UUID
    total: int
    new: int
    already_imported: int
    possible_duplicates: int
    invalid: int
    rows: list[PreviewRow]


class ImportRowConfirm(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    transaction_date: date
    description: str = Field(min_length=1, max_length=255)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    direction: Direction
    category: TransactionCategory


class ImportConfirmRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rows: list[ImportRowConfirm] = Field(min_length=1, max_length=MAX_ROWS)


class ImportResult(BaseModel):
    created: int
    skipped_already_imported: int
    transaction_ids: list[UUID]
