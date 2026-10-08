"""Layer 3: SQL for HMRC connections."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.hmrc.models import HmrcConnection, HmrcSubmission, HmrcTaxpayer


class HmrcConnectionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_for_landlord(self, landlord_id: UUID) -> HmrcConnection | None:
        stmt = select(HmrcConnection).where(HmrcConnection.landlord_id == landlord_id)
        return self._session.scalars(stmt).one_or_none()

    def add(self, connection: HmrcConnection) -> HmrcConnection:
        self._session.add(connection)
        self._session.flush()
        return connection

    def delete(self, connection: HmrcConnection) -> None:
        self._session.delete(connection)
        self._session.flush()

    def commit(self) -> None:
        self._session.commit()


class HmrcTaxpayerRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_for_landlord(self, landlord_id: UUID) -> HmrcTaxpayer | None:
        stmt = select(HmrcTaxpayer).where(HmrcTaxpayer.landlord_id == landlord_id)
        return self._session.scalars(stmt).one_or_none()

    def add(self, taxpayer: HmrcTaxpayer) -> HmrcTaxpayer:
        self._session.add(taxpayer)
        self._session.flush()
        return taxpayer

    def commit(self) -> None:
        self._session.commit()


class HmrcSubmissionRepository:
    """Append-only: there is deliberately no update or delete."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, submission: HmrcSubmission) -> HmrcSubmission:
        self._session.add(submission)
        self._session.flush()
        return submission

    def list_for_landlord(
        self, landlord_id: UUID, tax_year: int | None = None
    ) -> list[HmrcSubmission]:
        stmt = select(HmrcSubmission).where(HmrcSubmission.landlord_id == landlord_id)
        if tax_year is not None:
            stmt = stmt.where(HmrcSubmission.tax_year == tax_year)
        return list(self._session.scalars(stmt.order_by(HmrcSubmission.submitted_at.desc())))

    def commit(self) -> None:
        self._session.commit()
