"""Layer 4: a landlord's authorisation of LedgerLet at HMRC. Tokens are stored encrypted."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid
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
