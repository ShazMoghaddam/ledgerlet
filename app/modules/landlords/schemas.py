"""The landlords contract: the signed-in landlord's own profile and settings."""

from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.tax.periods import PeriodBasis


class LandlordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str | None
    display_name: str | None
    period_basis: PeriodBasis
    created_at: datetime


class LandlordUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    period_basis: PeriodBasis | None = None

    @model_validator(mode="after")
    def _basis_cannot_be_null(self) -> Self:
        if "period_basis" in self.model_fields_set and self.period_basis is None:
            raise ValueError("period_basis cannot be null")
        return self
