/**
 * The date ranges the transactions list can be filtered by, worked out from the
 * tax year's own dates (so a calendar-basis landlord gets 1 April, not 6 April).
 * Each has a short key for the URL: "2026", "2026-q2", "2026-to-q2", "all".
 *
 * "2026-to-q2" is what the quarter 2 update covers: the tax year from its start to
 * the end of quarter 2, because updates are cumulative. The Tax pages link to it.
 */
import type { Obligations } from "../api/types";
import { formatShort, type IsoDate } from "./dates";
import { quarterStates } from "./quarters";

export interface Period {
  key: string;
  label: string;
  from?: IsoDate;
  to?: IsoDate;
}

const shiftYear = (iso: IsoDate, by: number) => `${Number(iso.slice(0, 4)) + by}${iso.slice(4)}`;

export function periodsFor(obligations: Obligations, today: IsoDate): Period[] {
  const year = obligations.tax_year;
  const quarters = quarterStates(obligations.obligations, [], today);
  const first = quarters[0];
  const last = quarters[quarters.length - 1];
  if (!first || !last) return [{ key: "all", label: "All dates" }];
  const start = first.windowStart;
  const end = last.windowEnd;
  const label = (y: number) => `${y}-${String((y + 1) % 100).padStart(2, "0")}`;

  return [
    { key: String(year), label: `Tax year ${label(year)}`, from: start, to: end },
    ...quarters.map((q) => ({
      key: `${year}-q${q.quarter}`,
      label: `Quarter ${q.quarter} (${formatShort(q.windowStart)} to ${formatShort(q.windowEnd)})`,
      from: q.windowStart,
      to: q.windowEnd,
    })),
    // Quarter 1's update is quarter 1, and quarter 4's is the whole year: no extra entry.
    ...quarters.slice(1, -1).map((q) => ({
      key: `${year}-to-q${q.quarter}`,
      label: `Quarter ${q.quarter} update (${formatShort(start)} to ${formatShort(q.windowEnd)})`,
      from: start,
      to: q.windowEnd,
    })),
    {
      key: String(year - 1),
      label: `Tax year ${label(year - 1)}`,
      from: shiftYear(start, -1),
      to: shiftYear(end, -1),
    },
    { key: "all", label: "All dates" },
  ];
}

/** The period key for the figures in a quarterly update (see above). */
export function updatePeriodKey(taxYear: number, quarter: number): string {
  if (quarter === 1) return `${taxYear}-q1`;
  if (quarter === 4) return String(taxYear);
  return `${taxYear}-to-q${quarter}`;
}
