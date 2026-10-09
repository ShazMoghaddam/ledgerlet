/**
 * The date ranges the transactions list can be filtered by, worked out from the
 * tax year's own dates (so a calendar-basis landlord gets 1 April, not 6 April).
 * Each has a short key for the URL: "2026", "2026-q2", "all".
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
    {
      key: String(year - 1),
      label: `Tax year ${label(year - 1)}`,
      from: shiftYear(start, -1),
      to: shiftYear(end, -1),
    },
    { key: "all", label: "All dates" },
  ];
}
