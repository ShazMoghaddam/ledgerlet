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

/** 9600 -> "96.00": the form the API expects. Never a JavaScript number. */
export function toApiAmount(pence: Pence): string {
  if (!Number.isSafeInteger(pence) || pence < 0) throw new Error(`Bad amount: ${pence}`);
  return `${Math.trunc(pence / 100)}.${String(pence % 100).padStart(2, "0")}`;
}

export type AmountInput = { ok: true; pence: Pence } | { ok: false; error: string };

/**
 * What someone typed in an amount box, checked and turned into pence. Accepts the
 * ways people write money ("96", "96.5", "£1,200.00", " 1 200 ") and says plainly
 * what's wrong otherwise.
 */
export function parseAmountInput(text: string): AmountInput {
  const cleaned = text.replace(/[£,\s]/g, "");
  if (cleaned === "") return { ok: false, error: "Enter an amount, like 96.00" };
  if (cleaned.startsWith("-"))
    return {
      ok: false,
      error: "Enter the amount without a minus sign. Choose money in or out instead.",
    };
  if (!/^\d+(\.\d{1,2})?$/.test(cleaned)) {
    return /^\d+\.\d{3,}$/.test(cleaned)
      ? { ok: false, error: "Amounts can only have pence, like 96.50" }
      : { ok: false, error: "Enter an amount in pounds and pence, like 96.00" };
  }
  const pence = toPence(cleaned);
  if (pence === 0) return { ok: false, error: "Enter an amount more than £0.00" };
  if (pence >= 1_000_000_000_000)
    return { ok: false, error: "Enter an amount under £10,000,000,000" };
  return { ok: true, pence };
}
