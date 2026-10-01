import pytest
from pydantic import ValidationError

from app.modules.imports.schemas import CsvMapping


def test_signed_mapping_is_valid() -> None:
    CsvMapping(date_column="Date", description_column="Desc", amount_column="Amount")


def test_split_mapping_is_valid() -> None:
    CsvMapping(
        date_column="Date", description_column="Desc", paid_in_column="In", paid_out_column="Out"
    )


def test_blank_strings_count_as_not_given() -> None:
    m = CsvMapping(
        date_column="Date", description_column="Desc", amount_column="Amount", paid_in_column=""
    )
    assert m.paid_in_column is None


@pytest.mark.parametrize(
    "amount_fields",
    [
        {},
        {"paid_in_column": "In"},
        {"amount_column": "Amount", "paid_out_column": "Out"},
    ],
)
def test_must_choose_exactly_one_amount_style(amount_fields: dict[str, str]) -> None:
    with pytest.raises(ValidationError):
        CsvMapping(date_column="Date", description_column="Desc", **amount_fields)


def test_date_format_must_be_a_pattern() -> None:
    with pytest.raises(ValidationError):
        CsvMapping(
            date_column="Date", description_column="Desc", amount_column="A", date_format="DD/MM"
        )
