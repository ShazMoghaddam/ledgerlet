/**
 * Tax years by their start year (2026 means 6 April 2026 to 5 April 2027), as the
 * API does, and the addresses of the Tax pages.
 */
import type { IsoDate } from "./dates";

/** Quarterly updates began with the 2026-27 tax year. */
export const FIRST_TAX_YEAR = 2026;

/** The tax year a UK date falls in. Tax years start on 6 April whatever the update basis. */
export function taxYearOf(day: IsoDate): number {
  const year = Number(day.slice(0, 4));
  return day.slice(5) >= "04-06" ? year : year - 1;
}

/** "2026-27" */
export const taxYearLabel = (year: number) =>
  `${year}-${String((year + 1) % 100).padStart(2, "0")}`;

/** Read the year and quarter from an address like /tax/2026/q2. Undefined if it isn't one. */
export function parseTaxPath(year?: string, quarter?: string) {
  const y = year !== undefined && /^\d{4}$/.test(year) ? Number(year) : undefined;
  const q =
    quarter !== undefined && /^q[1-4]$/.test(quarter) ? Number(quarter.slice(1)) : undefined;
  return { year: y, quarter: q };
}

export const taxYearPath = (year: number, today: IsoDate) =>
  year === taxYearOf(today) ? "/tax" : `/tax/${year}`;
export const quarterPath = (year: number, quarter: number) => `/tax/${year}/q${quarter}`;
export const submitPath = (year: number, quarter: number) => `/tax/${year}/q${quarter}/submit`;
