"""Load LedgerLet's sample landlord into a local database. Development only.

    python scripts/seed_demo.py --sub shaz

Creates (or finds) the landlord you sign in as with scripts/dev_auth.py, then adds
two properties and their 2026-27 transactions to 3 October 2026. These are the same
figures the design boards use, so the app, the designs and the frontend tests agree:

    Quarter 2 (6 Apr to 5 Oct 2026), at your share
    Income                      £12,000.00   (Elm Court 7,200.00, Oak Road 4,800.00)
    Expenses                     £1,816.40   (Elm Court 1,336.40, Oak Road   480.00)
    Profit                      £10,183.60
    Residential finance costs    £2,940.00
    29 transactions

It goes through the normal services, so every business rule still applies. It
refuses to run against a production environment, or for a landlord who already
has properties (so it can't double up your data).
"""

import argparse
import sys
from collections.abc import Iterator
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

import app.models  # noqa: F401  (registers every table)
from app.core.auth import VerifiedIdentity
from app.core.config import get_settings
from app.core.database import get_sessionmaker
from app.modules.landlords.models import Landlord
from app.modules.landlords.repository import LandlordRepository
from app.modules.landlords.service import LandlordService
from app.modules.properties.repository import PropertyRepository
from app.modules.properties.schemas import PropertyCreate
from app.modules.properties.service import PropertyService
from app.modules.transactions.categories import TransactionCategory as Cat
from app.modules.transactions.repository import TransactionRepository
from app.modules.transactions.schemas import TransactionCreate
from app.modules.transactions.service import TransactionService

DEV_ISSUER = "http://localhost/dev-auth"  # matches scripts/dev_auth.py
DATA_TODAY = date(2026, 10, 9)  # the "today" the sample data is written for

ELM_COURT = PropertyCreate(
    nickname="Elm Court",
    address_line_1="Flat 4, Elm Court",
    town="Bristol",
    postcode="BS6 6AA",
    ownership_percentage=Decimal("100.00"),
)
OAK_ROAD = PropertyCreate(
    nickname="Oak Road",
    address_line_1="27 Oak Road",
    town="Leeds",
    postcode="LS6 2AB",
    ownership_percentage=Decimal("50.00"),  # owned jointly, half each
)

MONTHS = (5, 6, 7, 8, 9, 10)  # May to October 2026


def _tx(day: date, category: Cat, description: str, amount: str) -> TransactionCreate:
    return TransactionCreate(
        transaction_date=day, category=category, description=description, amount=Decimal(amount)
    )


def elm_court_transactions() -> Iterator[TransactionCreate]:
    for m in MONTHS:
        month = date(2026, m, 1).strftime("%B")
        yield _tx(date(2026, m, 2), Cat.RENTAL_INCOME, f"{month} rent", "1200.00")
        yield _tx(date(2026, m, 1), Cat.RESIDENTIAL_FINANCE_COSTS, "Mortgage interest", "490.00")
    yield _tx(date(2026, 6, 14), Cat.REPAIRS_AND_MAINTENANCE, "Gutter repair", "380.00")
    yield _tx(date(2026, 7, 15), Cat.PROFESSIONAL_FEES, "Tenancy renewal and referencing", "432.00")
    yield _tx(date(2026, 7, 22), Cat.REPAIRS_AND_MAINTENANCE, "Bathroom tap replacement", "212.00")
    yield _tx(date(2026, 9, 12), Cat.PREMISES_RUNNING_COSTS, "Landlord insurance renewal", "312.40")


def oak_road_transactions() -> Iterator[TransactionCreate]:
    for m in MONTHS:
        month = date(2026, m, 1).strftime("%B")
        yield _tx(date(2026, m, 1), Cat.RENTAL_INCOME, f"{month} rent", "1600.00")
        yield _tx(date(2026, m - 1, 28), Cat.PROFESSIONAL_FEES, "Letting agent fee", "144.00")
    yield _tx(date(2026, 10, 3), Cat.REPAIRS_AND_MAINTENANCE, "Boiler service", "96.00")


def seed(session: Session, issuer: str, subject: str, email: str | None = None) -> Landlord:
    landlord = LandlordService(LandlordRepository(session)).sign_in(
        VerifiedIdentity(issuer=issuer, subject=subject, email=email)
    )
    properties = PropertyService(PropertyRepository(session))
    if properties.list_properties(landlord.id, include_archived=True):
        raise SystemExit(f"{subject!r} already has properties. Nothing was added.")

    transactions = TransactionService(
        TransactionRepository(session), properties, today=lambda: DATA_TODAY
    )
    for details, rows in (
        (ELM_COURT, elm_court_transactions()),
        (OAK_ROAD, oak_road_transactions()),
    ):
        prop = properties.create_property(landlord.id, details)
        for row in rows:
            transactions.record_transaction(landlord.id, prop.id, row)
    return landlord


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--sub", required=True, help="the user id you sign in as, e.g. shaz")
    parser.add_argument("--email")
    args = parser.parse_args()

    if get_settings().environment == "production":
        sys.exit("Refusing to seed sample data into production.")
    with get_sessionmaker()() as session:
        seed(session, DEV_ISSUER, args.sub, args.email)
    print(f"Sample data added for {args.sub!r}: Elm Court, Oak Road and 29 transactions.")


if __name__ == "__main__":
    main()
