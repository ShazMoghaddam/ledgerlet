import { formatPounds, type FormatOptions } from "../lib/money";

/** An amount of money from the API, in tabular figures so columns line up. */
export function Amount({
  pounds,
  className,
  ...options
}: { pounds: string; className?: string } & FormatOptions) {
  return (
    <span className={["num", className].filter(Boolean).join(" ")}>
      {formatPounds(pounds, options)}
    </span>
  );
}
