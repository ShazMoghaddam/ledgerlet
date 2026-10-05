"""The module's contract: the shapes of data coming in and going out.

Schemas check *shape* (types, lengths, formats). Rules that need to look at
existing data (duplicates, ownership, archived state) belong in the service.
"""

from datetime import datetime
from decimal import Decimal
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.properties.validators import normalise_uk_postcode


class PropertyCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    nickname: str = Field(min_length=1, max_length=100, examples=["Flat 2, Elm Court"])
    address_line_1: str = Field(min_length=1, max_length=200)
    address_line_2: str | None = Field(default=None, max_length=200)
    town: str = Field(min_length=1, max_length=100)
    postcode: str = Field(examples=["SW1A 1AA"])
    # Your share for tax purposes, not necessarily the legal title. Married couples and
    # civil partners are taxed 50/50 unless HMRC has a Form 17 declaration.
    ownership_percentage: Decimal = Field(
        default=Decimal("100.00"),
        gt=0,
        le=100,
        max_digits=5,
        decimal_places=2,
        description="Your tax share of this property's income and expenses, in percent",
    )

    @field_validator("postcode")
    @classmethod
    def _normalise_postcode(cls, value: str) -> str:
        return normalise_uk_postcode(value)


class PropertyUpdate(BaseModel):
    """Partial update (PATCH): send only the fields you want to change."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    nickname: str | None = Field(default=None, min_length=1, max_length=100)
    address_line_1: str | None = Field(default=None, min_length=1, max_length=200)
    address_line_2: str | None = Field(default=None, max_length=200)
    town: str | None = Field(default=None, min_length=1, max_length=100)
    postcode: str | None = None
    ownership_percentage: Decimal | None = Field(
        default=None,
        gt=0,
        le=100,
        max_digits=5,
        decimal_places=2,
        description="Your tax share of this property's income and expenses, in percent",
    )

    @field_validator("postcode")
    @classmethod
    def _normalise_postcode(cls, value: str | None) -> str | None:
        return None if value is None else normalise_uk_postcode(value)

    @model_validator(mode="after")
    def _reject_null_for_required_fields(self) -> Self:
        # address_line_2 may be cleared with null; the others are required columns.
        required = ("nickname", "address_line_1", "town", "postcode", "ownership_percentage")
        for name in required:
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        return self


class PropertyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    nickname: str
    address_line_1: str
    address_line_2: str | None
    town: str
    postcode: str
    ownership_percentage: Decimal
    is_archived: bool
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime
