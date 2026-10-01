"""The two-step import workflow.

Collaborators (both Protocols, both satisfied by other modules' public services):
- PropertyLookup: does this landlord own the property, and is it active?
- TransactionGateway: what's already recorded, and record the new rows.
"""

from collections.abc import Callable, Sequence
from datetime import date
from typing import Protocol
from uuid import UUID

from app.core.exceptions import BusinessRuleError, ConflictError
from app.core.money import from_pence, to_pence
from app.core.time import uk_today
from app.modules.imports.fingerprint import FingerprintCounter
from app.modules.imports.parser import CsvFormatError, Direction, ParsedRow, parse_statement
from app.modules.imports.schemas import (
    MAX_ROWS,
    CsvMapping,
    ImportPreview,
    ImportResult,
    ImportRowConfirm,
    PreviewRow,
    RowStatus,
)
from app.modules.properties.models import Property
from app.modules.transactions.categories import TransactionCategory, TransactionKind
from app.modules.transactions.models import Transaction
from app.modules.transactions.schemas import TransactionCreate

KIND_FOR_DIRECTION = {Direction.IN: TransactionKind.INCOME, Direction.OUT: TransactionKind.EXPENSE}


class PropertyLookup(Protocol):
    def get_property(self, landlord_id: UUID, property_id: UUID) -> Property: ...


class TransactionGateway(Protocol):
    def list_transactions(
        self,
        landlord_id: UUID,
        property_id: UUID,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
        category: TransactionCategory | None = None,
    ) -> list[Transaction]: ...

    def record_imported_transactions(
        self,
        landlord_id: UUID,
        property_id: UUID,
        items: Sequence[tuple[TransactionCreate, str]],
    ) -> list[Transaction]: ...


class ImportService:
    def __init__(
        self,
        properties: PropertyLookup,
        transactions: TransactionGateway,
        today: Callable[[], date] = uk_today,
        max_rows: int = MAX_ROWS,
    ) -> None:
        self._properties = properties
        self._transactions = transactions
        self._today = today
        self._max_rows = max_rows

    # Step 1

    def preview(
        self, landlord_id: UUID, property_id: UUID, content: bytes, mapping: CsvMapping
    ) -> ImportPreview:
        self._ensure_importable(landlord_id, property_id)

        parsed = parse_statement(content, mapping)
        if not parsed:
            raise CsvFormatError("No transactions found in the file")
        if len(parsed) > self._max_rows:
            raise CsvFormatError(f"The file has {len(parsed)} rows; the limit is {self._max_rows}")

        today = self._today()
        counter = FingerprintCounter()
        staged: list[tuple[ParsedRow, str | None, str | None]] = []
        for row in parsed:
            if not row.is_valid:
                staged.append((row, None, row.error))
            elif row.transaction_date is not None and row.transaction_date > today:
                staged.append((row, None, "Date is in the future"))
            else:
                assert row.transaction_date and row.direction and row.amount is not None
                fp = counter.next(
                    row.transaction_date, row.direction, to_pence(row.amount), row.description
                )
                staged.append((row, fp, None))

        existing = self._existing(
            landlord_id, property_id, [r.transaction_date for r, fp, _ in staged if fp]
        )
        existing_fps = {t.import_fingerprint for t in existing if t.import_fingerprint}
        existing_keys = {(t.transaction_date, t.amount_pence) for t in existing}

        rows = [self._preview_row(r, fp, err, existing_fps, existing_keys) for r, fp, err in staged]
        return ImportPreview(
            property_id=property_id,
            total=len(rows),
            new=sum(r.status is RowStatus.NEW for r in rows),
            already_imported=sum(r.status is RowStatus.ALREADY_IMPORTED for r in rows),
            possible_duplicates=sum(r.status is RowStatus.POSSIBLE_DUPLICATE for r in rows),
            invalid=sum(r.status is RowStatus.INVALID for r in rows),
            rows=rows,
        )

    # Step 2

    def confirm(
        self, landlord_id: UUID, property_id: UUID, rows: Sequence[ImportRowConfirm]
    ) -> ImportResult:
        self._ensure_importable(landlord_id, property_id)

        # Validate everything first, so a bad row means nothing is saved.
        for index, row in enumerate(rows, start=1):
            expected = KIND_FOR_DIRECTION[row.direction]
            if row.category.kind is not expected:
                raise BusinessRuleError(
                    f"Row {index}: '{row.category.label}' is an {row.category.kind} category, "
                    f"but this money went {row.direction}"
                )

        existing = self._existing(landlord_id, property_id, [r.transaction_date for r in rows])
        already = {t.import_fingerprint for t in existing if t.import_fingerprint}

        to_create: list[tuple[TransactionCreate, str]] = []
        skipped = 0
        for row in rows:
            if row.fingerprint in already:
                skipped += 1
                continue
            already.add(row.fingerprint)  # also catches the same row sent twice
            to_create.append(
                (
                    TransactionCreate(
                        transaction_date=row.transaction_date,
                        category=row.category,
                        description=row.description,
                        amount=row.amount,
                    ),
                    row.fingerprint,
                )
            )

        created = (
            self._transactions.record_imported_transactions(landlord_id, property_id, to_create)
            if to_create
            else []
        )
        return ImportResult(
            created=len(created),
            skipped_already_imported=skipped,
            transaction_ids=[t.id for t in created],
        )

    # Helpers

    def _ensure_importable(self, landlord_id: UUID, property_id: UUID) -> None:
        prop = self._properties.get_property(landlord_id, property_id)
        if prop.is_archived:
            raise ConflictError("Can't import into an archived property. Restore it first.")

    def _existing(
        self, landlord_id: UUID, property_id: UUID, dates: Sequence[date]
    ) -> list[Transaction]:
        if not dates:
            return []
        return self._transactions.list_transactions(
            landlord_id, property_id, date_from=min(dates), date_to=max(dates)
        )

    @staticmethod
    def _preview_row(
        row: ParsedRow,
        fp: str | None,
        error: str | None,
        existing_fps: set[str],
        existing_keys: set[tuple[date, int]],
    ) -> PreviewRow:
        if fp is None:
            status, message = RowStatus.INVALID, error
        elif fp in existing_fps:
            status, message = RowStatus.ALREADY_IMPORTED, "Already imported"
        elif (
            row.amount is not None
            and (row.transaction_date, to_pence(row.amount)) in existing_keys
        ):
            status, message = (
                RowStatus.POSSIBLE_DUPLICATE,
                "A transaction with the same date and amount is already recorded",
            )
        else:
            status, message = RowStatus.NEW, None

        valid = fp is not None
        return PreviewRow(
            line=row.line,
            status=status,
            message=message,
            transaction_date=row.transaction_date,
            description=row.description,
            amount=from_pence(to_pence(row.amount)) if valid and row.amount else None,
            direction=row.direction if valid else None,
            suggested_kind=KIND_FOR_DIRECTION[row.direction] if valid and row.direction else None,
            fingerprint=fp,
        )
