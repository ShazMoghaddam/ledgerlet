import pytest

from app.modules.properties.validators import normalise_uk_postcode


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("SW1A 1AA", "SW1A 1AA"),
        ("sw1a1aa", "SW1A 1AA"),
        ("  ec1a   1bb ", "EC1A 1BB"),
        ("M1 1AE", "M1 1AE"),
        ("B33 8TH", "B33 8TH"),
        ("CR2 6XH", "CR2 6XH"),
        ("DN55 1PT", "DN55 1PT"),
        ("W1A 0AX", "W1A 0AX"),
    ],
)
def test_valid_postcodes_are_normalised(raw: str, expected: str) -> None:
    assert normalise_uk_postcode(raw) == expected


@pytest.mark.parametrize("raw", ["", "12345", "ABC", "SW1A", "SW1A 1A", "QQ1 1AA", "SW1A 1AAA"])
def test_invalid_postcodes_are_rejected(raw: str) -> None:
    with pytest.raises(ValueError):
        normalise_uk_postcode(raw)
