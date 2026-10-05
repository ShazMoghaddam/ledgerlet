"""HMRC Making Tax Digital update periods. Pure date logic: no database, no HTTP.

Rules encoded here (checked October 2026):
- The tax year runs 6 April to 5 April. Year "2026" means 2026-27.
- Quarterly updates are cumulative: every period starts at the beginning of
  the year, so Q2 covers April to October, not July to October.
- Standard periods end 5 Jul, 5 Oct, 5 Jan, 5 Apr and start on 6 April.
- Calendar periods (if the landlord elects them) end 30 Jun, 30 Sep, 31 Dec,
  31 Mar and start on 1 April.
- Deadlines are the same for both: 7 Aug, 7 Nov, 7 Feb, 7 May.
"""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class PeriodBasis(StrEnum):
    STANDARD = "standard"
    CALENDAR = "calendar"


class ObligationStatus(StrEnum):
    NOT_STARTED = "not_started"  # the tax year hasn't begun
    OPEN = "open"  # the period is still running
    DUE = "due"  # the period has ended; the deadline hasn't passed
    PAST_DEADLINE = "past_deadline"


QUARTERS = (1, 2, 3, 4)

# (years after the tax year's start year, month, day)
_PERIOD_ENDS = {
    PeriodBasis.STANDARD: ((0, 7, 5), (0, 10, 5), (1, 1, 5), (1, 4, 5)),
    PeriodBasis.CALENDAR: ((0, 6, 30), (0, 9, 30), (0, 12, 31), (1, 3, 31)),
}
_START_DAY = {PeriodBasis.STANDARD: 6, PeriodBasis.CALENDAR: 1}
_DEADLINES = ((0, 8), (0, 11), (1, 2), (1, 5))  # always the 7th
_DEADLINE_DAY = 7


def tax_year_containing(day: date) -> int:
    """The start year of the tax year a date falls in. 5 Apr 2026 -> 2025; 6 Apr 2026 -> 2026."""
    return day.year if day >= date(day.year, 4, 6) else day.year - 1


def tax_year_label(start_year: int) -> str:
    """2026 -> '2026-27'."""
    return f"{start_year}-{(start_year + 1) % 100:02d}"


@dataclass(frozen=True)
class UpdatePeriod:
    tax_year: int
    quarter: int
    basis: PeriodBasis
    start: date
    end: date
    deadline: date

    def contains(self, day: date) -> bool:
        return self.start <= day <= self.end

    def status(self, today: date) -> ObligationStatus:
        if today < self.start:
            return ObligationStatus.NOT_STARTED
        if today <= self.end:
            return ObligationStatus.OPEN
        if today <= self.deadline:
            return ObligationStatus.DUE
        return ObligationStatus.PAST_DEADLINE


def update_period(tax_year: int, quarter: int, basis: PeriodBasis) -> UpdatePeriod:
    if quarter not in QUARTERS:
        raise ValueError(f"quarter must be 1 to 4, not {quarter}")
    end_offset, end_month, end_day = _PERIOD_ENDS[basis][quarter - 1]
    deadline_offset, deadline_month = _DEADLINES[quarter - 1]
    return UpdatePeriod(
        tax_year=tax_year,
        quarter=quarter,
        basis=basis,
        start=date(tax_year, 4, _START_DAY[basis]),
        end=date(tax_year + end_offset, end_month, end_day),
        deadline=date(tax_year + deadline_offset, deadline_month, _DEADLINE_DAY),
    )


def update_periods(tax_year: int, basis: PeriodBasis) -> list[UpdatePeriod]:
    return [update_period(tax_year, q, basis) for q in QUARTERS]
