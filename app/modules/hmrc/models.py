"""Layer 4: a landlord's authorisation of LedgerLet at HMRC. Tokens are stored encrypted."""

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin


class HmrcConnection(TimestampMixin, Base):
    __tablename__ = "hmrc_connections"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)

    # One connection per landlord. CASCADE: if the landlord goes, so do their HMRC tokens.
    landlord_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("landlords.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    # Fernet ciphertext, never the raw tokens.
    access_token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)

    access_token_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    scope: Mapped[str] = mapped_column(String(255), nullable=False)
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    def __repr__(self) -> str:
        return f"<HmrcConnection landlord={self.landlord_id}>"


class HmrcTaxpayer(TimestampMixin, Base):
    """Who the landlord is at HMRC: their NINO (encrypted) and UK property business id.

    Kept apart from HmrcConnection on purpose: disconnecting from HMRC, or an expired
    grant, removes the tokens but shouldn't make the landlord re-enter their NINO.
    """

    __tablename__ = "hmrc_taxpayers"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    landlord_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("landlords.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    nino_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    uk_property_business_id: Mapped[str | None] = mapped_column(String(32), nullable=True)


class HmrcSubmission(Base):
    """Audit trail: one row per attempt to send figures to HMRC. Append-only, never edited.

    Holds exactly what was sent and exactly what HMRC said, so any figure a landlord
    filed can be traced and explained later. The NINO is deliberately not stored here.
    """

    __tablename__ = "hmrc_submissions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    # RESTRICT: a filing record must outlive everything else about the landlord.
    landlord_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("landlords.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    business_id: Mapped[str] = mapped_column(String(32), nullable=False)
    tax_year: Mapped[int] = mapped_column(Integer, nullable=False)
    quarter: Mapped[int] = mapped_column(Integer, nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    consolidated_expenses: Mapped[bool] = mapped_column(Boolean, nullable=False)
    request_body: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    succeeded: Mapped[bool] = mapped_column(Boolean, nullable=False)
    hmrc_correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    response_body: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
