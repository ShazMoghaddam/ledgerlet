"""Custom column types shared across modules."""

from enum import StrEnum

from sqlalchemy import String
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator


class StrEnumType(TypeDecorator[StrEnum]):
    """Stores a StrEnum as plain VARCHAR; Python code always sees the enum.

    Chosen over native Postgres enums because adding a category later is then
    a simple CHECK constraint change rather than an ALTER TYPE migration.
    """

    impl = String
    cache_ok = True

    def __init__(self, enum_cls: type[StrEnum], length: int) -> None:
        super().__init__(length=length)
        self._enum_cls = enum_cls

    def process_bind_param(self, value: StrEnum | str | None, dialect: Dialect) -> str | None:
        return None if value is None else self._enum_cls(value).value

    def process_result_value(self, value: str | None, dialect: Dialect) -> StrEnum | None:
        return None if value is None else self._enum_cls(value)


def sql_in_list(enum_cls: type[StrEnum]) -> str:
    """Render enum values for a CHECK constraint, e.g. 'a', 'b', 'c'."""
    return ", ".join(f"'{member.value}'" for member in enum_cls)
