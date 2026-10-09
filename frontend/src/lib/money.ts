/**
 * Money in the browser, without floating point.
 *
 * The API sends amounts as strings of pounds ("1200.00"). We turn them into whole
 * pence (integers) straight from the string, and format pence back to text the same
 * way. A number like 0.1 + 0.2 never appears, so totals can't drift by a penny.
 */

export type Pence = number; // always a whole number

const AMOUNT = /^(-)?(\d+)(?:\.(\d{1,2}))?$/;

/** "1200.00" -> 120000. Throws on anything that isn't a plain amount of pounds. */
export function toPence(pounds: string): Pence {
  const match = AMOUNT.exec(pounds.trim());
  if (!match) throw new Error(`Not an amount of money: ${JSON.stringify(pounds)}`);
  const [, minus, whole = "0", fraction = ""] = match;
  const pence = Number(whole) * 100 + Number(fraction.padEnd(2, "0"));
  if (!Number.isSafeInteger(pence)) throw new Error(`Amount too large: ${pounds}`);
  return minus ? -pence : pence;
}

const grouping = new Intl.NumberFormat("en-GB", { useGrouping: true, maximumFractionDigits: 0 });

export interface FormatOptions {
  /** Show "£". On by default; off inside tables where the column says it. */
  symbol?: boolean;
  /** "+" for money in, "−" for money out, as on the phone list. */
  signed?: boolean;
}

/** 120000 -> "£1,200.00". Uses a true minus sign (U+2212), as typeset statements do. */
export function formatPence(pence: Pence, { symbol = true, signed = false }: FormatOptions = {}) {
  if (!Number.isSafeInteger(pence)) throw new Error(`Not a whole number of pence: ${pence}`);
  const abs = Math.abs(pence);
  const pounds = grouping.format(Math.trunc(abs / 100));
  const rest = String(abs % 100).padStart(2, "0");
  const sign = pence < 0 ? "−" : signed && pence > 0 ? "+" : "";
  return `${sign}${symbol ? "£" : ""}${pounds}.${rest}`;
}

/** Straight from an API string to display text. */
export function formatPounds(pounds: string, options?: FormatOptions) {
  return formatPence(toPence(pounds), options);
}
