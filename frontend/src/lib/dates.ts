/**
 * Dates as the API sends them ("2026-10-03"): calendar days with no time or zone.
 *
 * They're handled in UTC internally so a day never shifts when someone's clock is in
 * another time zone. "Today" is today in the UK, because UK tax rules use UK dates.
 */

export type IsoDate = string; // "YYYY-MM-DD"

function toUtc(iso: IsoDate): Date {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
  if (!match) throw new Error(`Not a date: ${JSON.stringify(iso)}`);
  const [, y, m, d] = match;
  return new Date(Date.UTC(Number(y), Number(m) - 1, Number(d)));
}

const fmt = (options: Intl.DateTimeFormatOptions) =>
  new Intl.DateTimeFormat("en-GB", { timeZone: "UTC", ...options });
// Written out, because browsers disagree on "Sep" and "Sept" for en-GB.
const SHORT_MONTHS = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
];
const dayMonthYear = fmt({ day: "numeric", month: "long", year: "numeric" });
const monthYear = fmt({ month: "long", year: "numeric" });

/** "3 Oct" */
export function formatShort(iso: IsoDate): string {
  const d = toUtc(iso);
  return `${d.getUTCDate()} ${SHORT_MONTHS[d.getUTCMonth()]}`;
}
/** "3 October 2026" */
export const formatLong = (iso: IsoDate) => dayMonthYear.format(toUtc(iso));
/** "October 2026" */
export const formatMonth = (iso: IsoDate) => monthYear.format(toUtc(iso));

/** Today's date in the UK, whatever the device's time zone. */
export function ukToday(now: Date = new Date()): IsoDate {
  // en-CA formats as YYYY-MM-DD.
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/London" }).format(now);
}

const DAY_MS = 86_400_000;

/** Whole days from a to b (negative if b is earlier). */
export function daysBetween(a: IsoDate, b: IsoDate): number {
  return Math.round((toUtc(b).getTime() - toUtc(a).getTime()) / DAY_MS);
}

export function addDays(iso: IsoDate, days: number): IsoDate {
  return new Date(toUtc(iso).getTime() + days * DAY_MS).toISOString().slice(0, 10);
}

/** Position of a day between two others, from 0 to 1. Used to draw the tax-year ruler. */
export function fractionOfSpan(day: IsoDate, start: IsoDate, end: IsoDate): number {
  const span = daysBetween(start, end);
  if (span <= 0) return 0;
  return Math.min(1, Math.max(0, daysBetween(start, day) / span));
}

const dayLongMonth = fmt({ day: "numeric", month: "long" });
/** "5 October": for sentences where the year is obvious. */
export const formatDayMonth = (iso: IsoDate) => dayLongMonth.format(toUtc(iso));
