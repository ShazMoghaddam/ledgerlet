"""Date logic is where tax software usually goes wrong, so every boundary is pinned."""

from datetime import date

import pytest

from app.modules.tax.periods import (
    ObligationStatus,
    PeriodBasis,
    tax_year_containing,
    tax_year_label,
    update_period,
    update_periods,
)

STANDARD, CALENDAR = PeriodBasis.STANDARD, PeriodBasis.CALENDAR


def test_standard_periods_match_hmrc_table() -> None:
    periods = update_periods(2026, STANDARD)
    assert [(p.start, p.end, p.deadline) for p in periods] == [
        (date(2026, 4, 6), date(2026, 7, 5), date(2026, 8, 7)),
        (date(2026, 4, 6), date(2026, 10, 5), date(2026, 11, 7)),
        (date(2026, 4, 6), date(2027, 1, 5), date(2027, 2, 7)),
        (date(2026, 4, 6), date(2027, 4, 5), date(2027, 5, 7)),
    ]


def test_calendar_periods_match_hmrc_table() -> None:
    periods = update_periods(2026, CALENDAR)
    assert [(p.start, p.end) for p in periods] == [
        (date(2026, 4, 1), date(2026, 6, 30)),
        (date(2026, 4, 1), date(2026, 9, 30)),
        (date(2026, 4, 1), date(2026, 12, 31)),
        (date(2026, 4, 1), date(2027, 3, 31)),
    ]


def test_deadlines_are_the_same_for_both_bases() -> None:
    assert [p.deadline for p in update_periods(2026, CALENDAR)] == [
        p.deadline for p in update_periods(2026, STANDARD)
    ]


def test_periods_are_cumulative_from_the_year_start() -> None:
    assert {p.start for p in update_periods(2026, STANDARD)} == {date(2026, 4, 6)}


@pytest.mark.parametrize(
    ("day", "year"),
    [
        (date(2026, 4, 5), 2025),
        (date(2026, 4, 6), 2026),
        (date(2026, 12, 31), 2026),
        (date(2027, 1, 1), 2026),
        (date(2027, 4, 5), 2026),
    ],
)
def test_tax_year_containing(day: date, year: int) -> None:
    assert tax_year_containing(day) == year


def test_tax_year_label() -> None:
    assert tax_year_label(2026) == "2026-27"
    assert tax_year_label(2099) == "2099-00"


def test_q1_boundaries() -> None:
    q1 = update_period(2026, 1, STANDARD)
    assert not q1.contains(date(2026, 4, 5))
    assert q1.contains(date(2026, 4, 6))
    assert q1.contains(date(2026, 7, 5))
    assert not q1.contains(date(2026, 7, 6))


@pytest.mark.parametrize(
    ("today", "status"),
    [
        (date(2026, 4, 5), ObligationStatus.NOT_STARTED),
        (date(2026, 7, 5), ObligationStatus.OPEN),
        (date(2026, 7, 6), ObligationStatus.DUE),
        (date(2026, 8, 7), ObligationStatus.DUE),
        (date(2026, 8, 8), ObligationStatus.PAST_DEADLINE),
    ],
)
def test_q1_status_over_time(today: date, status: ObligationStatus) -> None:
    assert update_period(2026, 1, STANDARD).status(today) is status


def test_invalid_quarter() -> None:
    with pytest.raises(ValueError):
        update_period(2026, 5, STANDARD)
