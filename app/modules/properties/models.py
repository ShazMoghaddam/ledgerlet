"""Layer 4, the data model: what a property looks like in the database."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin


class Property(TimestampMixin, Base):
    __tablename__ = "properties"
    __table_args__ = (
        # Defence in depth: the API validates this too, but the database is the
        # last line of defence against bad data from any source.
        CheckConstraint(
            "ownership_percentage > 0 AND ownership_percentage <= 100",
            name="ownership_percentage_range",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)

    # Owner. Becomes a foreign key to landlords.id when the auth module adds
    # that table (a one-line migration). Indexed: every query filters on it.
    landlord_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)

    nickname: Mapped[str] = mapped_column(String(100), nullable=False)
    address_line_1: Mapped[str] = mapped_column(String(200), nullable=False)
    address_line_2: Mapped[str | None] = mapped_column(String(200), nullable=True)
    town: Mapped[str] = mapped_column(String(100), nullable=False)
    postcode: Mapped[str] = mapped_column(String(8), nullable=False)

    # Share of the property this landlord owns. Jointly owned properties are
    # common, and tax is split by share, so the MTD figures depend on it.
    ownership_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("100.00"), server_default="100.00"
    )

    # Soft delete. Properties carry financial history HMRC can ask about for
    # years, so we archive rather than delete.
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @property
    def is_archived(self) -> bool:
        return self.archived_at is not None

    def __repr__(self) -> str:
        return f"<Property {self.id} {self.nickname!r}>"
