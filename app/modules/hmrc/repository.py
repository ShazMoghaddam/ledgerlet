"""Layer 3: SQL for HMRC connections."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.hmrc.models import HmrcConnection, HmrcTaxpayer


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
