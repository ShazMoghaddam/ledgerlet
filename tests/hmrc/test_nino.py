import pytest

from app.modules.hmrc.nino import mask_nino, normalise_nino


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("oe 18 06 77 a", "OE180677A"), ("AB123456C", "AB123456C"), ("tw000000d", "TW000000D")],
)
def test_valid(raw: str, expected: str) -> None:
    assert normalise_nino(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "QQ123456C",  # Q is never a prefix letter
        "BG123456A",  # never-issued pair
        "AO123456A",  # O is never the second letter
        "DA123456A",  # D is never a prefix letter
        "AB123456E",  # suffix only A to D
        "AB12345C",
        "AB1234567C",
    ],
)
def test_invalid(raw: str) -> None:
    with pytest.raises(ValueError):
        normalise_nino(raw)


def test_mask() -> None:
    assert mask_nino("OE180677A") == "OE****77A"
