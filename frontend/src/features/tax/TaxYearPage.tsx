import { Link, useParams } from "react-router";

import { useObligations, useSubmissions, useSummary } from "../../api/queries";
import { LoadFailed, Loading } from "../../components/QueryState";
import { Statement, whoseProperties } from "../../components/Statement";
import { WIDE, useMediaQuery } from "../../hooks/useMediaQuery";
import { usePageTitle } from "../../hooks/usePageTitle";
import { formatDayMonth, formatLong, formatShort, ukToday } from "../../lib/dates";
import { currentQuarter, quarterStates, type Quarter } from "../../lib/quarters";
import {
  FIRST_TAX_YEAR,
  parseTaxPath,
  quarterPath,
  taxYearLabel,
  taxYearOf,
  taxYearPath,
} from "../../lib/taxYear";
import { NotFoundPage } from "../placeholder/SectionPlaceholder";
import { QuarterStatus } from "./QuarterStatus";
import s from "./Tax.module.css";

/** /tax (this tax year) and /tax/2026. */
export function TaxYearPage({ today = ukToday() }: { today?: string }) {
  const params = useParams();
  const { year } = parseTaxPath(params.year);
  if (params.year !== undefined && year === undefined) return <NotFoundPage />;
  return <TaxYear year={year ?? taxYearOf(today)} today={today} />;
}

function TaxYear({ year, today }: { year: number; today: string }) {
  const label = `Tax year ${taxYearLabel(year)}`;
  usePageTitle(label);
  const thisYear = taxYearOf(today);

  if (year < FIRST_TAX_YEAR || year > thisYear)
    return (
      <div className={s.page}>
        <h1 id="page-heading" tabIndex={-1}>
          {label}
        </h1>
        <p className={s.lead}>
          {year < FIRST_TAX_YEAR
            ? `Quarterly updates to HMRC started with the ${taxYearLabel(FIRST_TAX_YEAR)} tax year, so there’s nothing to send for ${taxYearLabel(year)}.`
            : `The ${taxYearLabel(year)} tax year hasn’t started yet.`}
        </p>
        <p>
          <Link to="/tax">Go to this tax year</Link>
        </p>
      </div>
    );

  return (
    <div className={s.page}>
      <h1 id="page-heading" tabIndex={-1}>
        {label}
      </h1>
      <YearContents year={year} today={today} />
      <OtherYears year={year} thisYear={thisYear} today={today} />
    </div>
  );
}

function YearContents({ year, today }: { year: number; today: string }) {
  const obligations = useObligations(year);
  const submissions = useSubmissions(year);

  if (obligations.isPending) return <Loading label="the tax year" />;
  if (obligations.isError)
    return <LoadFailed what="the tax year" error={obligations.error} retry={obligations.refetch} />;

  const known = submissions.isSuccess;
  const quarters = quarterStates(obligations.data.obligations, submissions.data ?? [], today);
  const yearStart = quarters[0]?.windowStart;
  const yearEnd = quarters[quarters.length - 1]?.windowEnd;
  const current = currentQuarter(quarters);

  return (
    <>
      <section className={s.section} aria-labelledby="updates-heading">
        <h2 id="updates-heading">Quarterly updates</h2>
        {submissions.isError && (
          <LoadFailed
            what="what you’ve sent to HMRC"
            error={submissions.error}
            retry={submissions.refetch}
          />
        )}
        {submissions.isPending && <Loading label="what you’ve sent to HMRC" />}
        <QuarterTable year={year} quarters={quarters} known={known} />
        {yearStart && (
          <p className={s.note}>
            Each update covers the tax year so far, from {formatDayMonth(yearStart)} to the end of
            that quarter. So sending one also brings the earlier quarters up to date.
          </p>
        )}
      </section>

      {current && yearStart && (
        <YearSoFar year={year} start={yearStart} quarter={current} today={today} />
      )}

      {yearEnd && (
        <section className={s.section} aria-labelledby="eoy-heading">
          <h2 id="eoy-heading">End of year</h2>
          <p className={s.prose}>
            After quarter 4 you confirm the year’s figures and make your final declaration, by{" "}
            {formatLong(`${year + 2}-01-31`)}. LedgerLet will guide you through this in a later
            update.
          </p>
        </section>
      )}
    </>
  );
}

/** A table on tablets and up; on a phone each quarter is one tappable row. */
function QuarterTable({
  year,
  quarters,
  known,
}: {
  year: number;
  quarters: Quarter[];
  known: boolean;
}) {
  const wide = useMediaQuery(WIDE);
  const start = quarters[0]?.windowStart ?? "";
  // The last quarter ends the day before the year began, a year on: say which year.
  const covers = (q: Quarter) =>
    `${formatShort(start)} to ${formatShort(q.windowEnd)}${q.quarter === quarters.length ? ` ${q.windowEnd.slice(0, 4)}` : ""}`;
  const action = (q: Quarter) => {
    switch (q.state.kind) {
      case "ready":
      case "overdue":
        return known ? "Review" : "View";
      case "sent":
      case "in_progress":
        return "View";
      case "not_started":
        return undefined;
    }
  };

  if (!wide)
    return (
      <ul className={s.quarterList}>
        {quarters.map((q) => {
          const text = action(q);
          const body = (
            <>
              <span className={s.quarterName}>Quarter {q.quarter}</span>
              <span className={s.meta}>
                {covers(q)}, due {formatShort(q.deadline)}
              </span>
              <QuarterStatus quarter={q} known={known} />
            </>
          );
          return (
            <li key={q.quarter}>
              {text ? (
                <Link to={quarterPath(year, q.quarter)} className={s.quarterRow}>
                  {body}
                </Link>
              ) : (
                <div className={s.quarterRow}>{body}</div>
              )}
            </li>
          );
        })}
      </ul>
    );

  return (
    <table className={`${s.table} num`}>
      <caption className="visually-hidden">The four quarterly updates for the year</caption>
      <thead>
        <tr>
          <th scope="col">Quarter</th>
          <th scope="col">Covers</th>
          <th scope="col">Due</th>
          <th scope="col">Status</th>
          <th scope="col">
            <span className="visually-hidden">Action</span>
          </th>
        </tr>
      </thead>
      <tbody>
        {quarters.map((q) => {
          const text = action(q);
          return (
            <tr key={q.quarter}>
              <th scope="row">Quarter {q.quarter}</th>
              <td>{covers(q)}</td>
              <td>{formatShort(q.deadline)}</td>
              <td>
                <QuarterStatus quarter={q} known={known} />
              </td>
              <td className={s.action}>
                {text && (
                  <Link to={quarterPath(year, q.quarter)}>
                    {text}
                    <span className="visually-hidden"> quarter {q.quarter}</span>
                  </Link>
                )}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

function YearSoFar({
  year,
  start,
  quarter,
  today,
}: {
  year: number;
  start: string;
  quarter: Quarter;
  today: string;
}) {
  const summary = useSummary(year, quarter.quarter);
  const ended = today > quarter.windowEnd;
  return (
    <section className={s.section} aria-labelledby="ytd-heading">
      <div className={s.headText}>
        <h2 id="ytd-heading">Year so far</h2>
        <p className={s.meta}>
          {formatDayMonth(start)} to {ended ? formatDayMonth(quarter.windowEnd) : "today"}
        </p>
      </div>
      {summary.isPending ? (
        <Loading label="your figures" />
      ) : summary.isError ? (
        <LoadFailed what="your figures" error={summary.error} retry={summary.refetch} />
      ) : (
        <div className={s.statementWrap}>
          <Statement
            totals={summary.data.totals}
            whose={whoseProperties(summary.data.properties.length)}
          />
        </div>
      )}
    </section>
  );
}

function OtherYears({ year, thisYear, today }: { year: number; thisYear: number; today: string }) {
  const others: number[] = [];
  for (let y = thisYear; y >= FIRST_TAX_YEAR; y--) if (y !== year) others.push(y);
  if (others.length === 0) return null;
  return (
    <nav aria-label="Other tax years" className={s.section}>
      <h2 className={s.small}>Other tax years</h2>
      <ul className={s.inlineList}>
        {others.map((y) => (
          <li key={y}>
            <Link to={taxYearPath(y, today)}>Tax year {taxYearLabel(y)}</Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}
