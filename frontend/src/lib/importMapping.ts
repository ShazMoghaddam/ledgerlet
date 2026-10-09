/**
 * A first guess at which column is which, from the names UK banks use. Only a
 * guess: the landlord sees it, with examples, and can change any of it.
 */
export type AmountStyle = "signed" | "split";

export interface Mapping {
  dateColumn: string;
  descriptionColumn: string;
  amountStyle: AmountStyle;
  amountColumn: string;
  paidInColumn: string;
  paidOutColumn: string;
  dateFormat: string;
  invertSign: boolean;
}

export const DATE_FORMATS: { value: string; label: string; pattern: RegExp }[] = [
  { value: "%d/%m/%Y", label: "31/12/2026", pattern: /^\d{1,2}\/\d{1,2}\/\d{4}$/ },
  { value: "%d/%m/%y", label: "31/12/26", pattern: /^\d{1,2}\/\d{1,2}\/\d{2}$/ },
  { value: "%Y-%m-%d", label: "2026-12-31", pattern: /^\d{4}-\d{2}-\d{2}$/ },
  { value: "%d-%m-%Y", label: "31-12-2026", pattern: /^\d{1,2}-\d{1,2}-\d{4}$/ },
  { value: "%d %b %Y", label: "31 Dec 2026", pattern: /^\d{1,2} [A-Za-z]{3} \d{4}$/ },
];

const find = (columns: string[], ...patterns: RegExp[]) => {
  for (const p of patterns) {
    const hit = columns.find((c) => p.test(c.trim()));
    if (hit) return hit;
  }
  return "";
};

export function guessMapping(columns: string[], examples: string[][]): Mapping {
  const dateColumn = find(columns, /^(transaction |posting )?date$/i, /date/i);
  const descriptionColumn = find(
    columns,
    /^description$/i,
    /description|details|narrative|payee|merchant|memo|reference|name/i,
  );
  const amountColumn = find(columns, /^amount( \(gbp\)| \(£\))?$/i, /^value$/i, /amount/i);
  const paidInColumn = find(columns, /paid in|money in|credit|deposit|^in( \(£\))?$/i);
  const paidOutColumn = find(columns, /paid out|money out|debit|withdrawal|^out( \(£\))?$/i);
  const amountStyle: AmountStyle =
    !amountColumn && paidInColumn && paidOutColumn ? "split" : "signed";

  const dateIndex = columns.indexOf(dateColumn);
  const sample = examples.map((row) => row[dateIndex] ?? "").find((v) => v !== "") ?? "";
  const dateFormat = DATE_FORMATS.find((f) => f.pattern.test(sample))?.value ?? "%d/%m/%Y";

  return {
    dateColumn,
    descriptionColumn,
    amountStyle,
    amountColumn,
    paidInColumn,
    paidOutColumn,
    dateFormat,
    invertSign: false,
  };
}
