"""Layer 4: a landlord, linked to an identity at the provider."""

import uuid

from sqlalchemy import CheckConstraint, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin
from app.core.types import StrEnumType, sql_in_list
from app.modules.tax.periods import PeriodBasis


class Landlord(TimestampMixin, Base):
    __tablename__ = "landlords"
    __table_args__ = (
        # A subject id is only unique within its issuer, so the pair is the identity.
        UniqueConstraint(
            "auth_issuer", "auth_subject", name="uq_landlords_auth_issuer_auth_subject"
        ),
        CheckConstraint(f"period_basis IN ({sql_in_list(PeriodBasis)})", name="period_basis_valid"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    auth_issuer: Mapped[str] = mapped_column(String(255), nullable=False)
    auth_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Standard (6 Apr...) or calendar (1 Apr...) update periods, as elected with HMRC.
    period_basis: Mapped[PeriodBasis] = mapped_column(
        StrEnumType(PeriodBasis, length=20),
        nullable=False,
        default=PeriodBasis.STANDARD,
        server_default=PeriodBasis.STANDARD.value,
    )

    def __repr__(self) -> str:
        return f"<Landlord {self.id}>"
