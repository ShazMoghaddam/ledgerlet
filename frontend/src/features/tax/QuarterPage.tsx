import type { ReactNode } from "react";
import { Link, useParams } from "react-router";

import {
  useHmrcConnection,
  useObligations,
  useSubmissions,
  useSummary,
  useTaxpayer,
} from "../../api/queries";
import type { CategoryAmount, PropertySummary, Submission, TaxSummary } from "../../api/types";
import { Amount } from "../../components/Amount";
import { ButtonLink } from "../../components/Button";
import { AlertIcon, CheckIcon } from "../../components/Icons";
import { LoadFailed, Loading } from "../../components/QueryState";
import { whoseProperties } from "../../components/Statement";
import { WIDE, useMediaQuery } from "../../hooks/useMediaQuery";
import { usePageTitle } from "../../hooks/usePageTitle";
import { formatDayMonth, formatLong, formatShort, ukToday } from "../../lib/dates";
import { toPence } from "../../lib/money";
import { ownsAll, trimPercentage } from "../../lib/ownership";
import { updatePeriodKey } from "../../lib/periods";
import { quarterStates, type Quarter } from "../../lib/quarters";
import {
  FIRST_TAX_YEAR,
  parseTaxPath,
  quarterPath,
  submitPath,
  taxYearLabel,
  taxYearOf,
  taxYearPath,
} from "../../lib/taxYear";
import { NotFoundPage } from "../placeholder/SectionPlaceholder";
import s from "./Tax.module.css";

const FINANCE = "residential_finance_costs";

/** /tax/2026/q2: what one quarterly update will send, and whether it can be sent. */
export function QuarterPage({ today = ukToday() }: { today?: string }) {
  const params = useParams();
  const { year, quarter } = parseTaxPath(params.year, params.quarter);
  if (
    year === undefined ||
    quarter === undefined ||
    year < FIRST_TAX_YEAR ||
    year > taxYearOf(today)
  )
    return <NotFoundPage />;
  return <QuarterView key={`${year}-${quarter}`} year={year} quarter={quarter} today={today} />;
}

function QuarterView({ year, quarter, today }: { year: number; quarter: number; today: string }) {
  usePageTitle(`Quarter ${quarter}, ${taxYearLabel(year)}`);
  const obligations = useObligations(year);
  const submissions = useSubmissions(year);
  const summary = useSummary(year, quarter);

  const quarters = obligations.data
    ? quarterStates(obligations.data.obligations, submissions.data ?? [], today)
    : [];
  const q = quarters.find((x) => x.quarter === quarter);
  const yearStart = quarters[0]?.windowStart;

  return (
    <div className={s.page}>
      <nav aria-label="Breadcrumb" className={s.breadcrumb}>
        <Link to={taxYearPath(year, today)}>Tax year {taxYearLabel(year)}</Link>
        <span aria-hidden="true"> / </span>
        <span aria-current="page">Quarter {quarter}</span>
      </nav>

      <header className={s.head}>
        <div className={s.headText}>
          <h1 id="page-heading" tabIndex={-1}>
            Quarter {quarter}
          </h1>
          {q && yearStart && (
            <p className={s.lead}>
              {yearStart.slice(0, 4) === q.windowEnd.slice(0, 4)
                ? formatDayMonth(yearStart)
                : formatLong(yearStart)}{" "}
              to {formatLong(q.windowEnd)}: the tax year so far. Due by {formatLong(q.deadline)}.
            </p>
          )}
        </div>
        <nav aria-label="Quarters" className={s.switcher}>
          {[1, 2, 3, 4].map((n) => (
            <Link
              key={n}
              to={quarterPath(year, n)}
              aria-current={n === quarter ? "page" : undefined}
            >
              Q{n}
            </Link>
          ))}
        </nav>
      </header>

      {obligations.isPending ? (
        <Loading label="the quarter" />
      ) : obligations.isError ? (
        <LoadFailed what="the quarter" error={obligations.error} retry={obligations.refetch} />
      ) : q ? (
        <div className={s.layout}>
          <aside className={s.panel} aria-labelledby="send-heading">
            <SendPanel
              year={year}
              quarter={q}
              earlier={quarters.filter((x) => x.quarter < quarter)}
              submissions={submissions.data}
              submissionsError={submissions.error}
              retrySubmissions={submissions.refetch}
              today={today}
            />
          </aside>
          <section className={s.figures} aria-labelledby="figures-heading">
            <h2 id="figures-heading">
              {q.state.kind === "sent"
                ? "Figures as they are now"
                : q.state.kind === "in_progress" || q.state.kind === "not_started"
                  ? "Figures so far"
                  : "What HMRC will receive"}
            </h2>
            {summary.isPending ? (
              <Loading label="the figures" />
            ) : summary.isError ? (
              <LoadFailed what="the figures" error={summary.error} retry={summary.refetch} />
            ) : (
              <Figures summary={summary.data} year={year} quarter={quarter} />
            )}
          </section>
        </div>
      ) : null}
    </div>
  );
}

/* ---------- Can it be sent? ---------- */

function SendPanel({
  year,
  quarter: q,
  earlier,
  submissions,
  submissionsError,
  retrySubmissions,
  today,
}: {
  year: number;
  quarter: Quarter;
  earlier: Quarter[];
  submissions?: Submission[];
  submissionsError: Error | null;
  retrySubmissions: () => void;
  today: string;
}) {
  const connection = useHmrcConnection();
  const connected = connection.data?.connected === true;
  const taxpayer = useTaxpayer(connected);
  const ended = today > q.windowEnd;
  const state = q.state.kind;

  if (state === "not_started" || state === "in_progress")
    return (
      <>
        <h2 id="send-heading">{state === "in_progress" ? "In progress" : "Not started"}</h2>
        <p className={s.prose}>
          {state === "in_progress"
            ? `Keep recording income and expenses. You can send this update once the quarter ends on ${formatLong(q.windowEnd)}. HMRC needs it by ${formatLong(q.deadline)}.`
            : `This quarter starts on ${formatLong(q.windowStart)}.`}
        </p>
        {state === "in_progress" && (
          <ButtonLink to="/transactions/new" variant="secondary">
            Add transaction
          </ButtonLink>
        )}
      </>
    );

  if (submissionsError)
    return (
      <>
        <h2 id="send-heading">Ended {formatShort(q.windowEnd)}</h2>
        <LoadFailed
          what="what you’ve sent to HMRC"
          error={submissionsError}
          retry={retrySubmissions}
        />
      </>
    );
  if (!submissions) return <Loading label="what you’ve sent to HMRC" />;

  const business = taxpayer.data?.nino && taxpayer.data.uk_property_business_id;
  const canSend = ended && connected && Boolean(business);

  const checks: Check[] = [
    { ok: ended, text: `Quarter ended ${formatShort(q.windowEnd)}` },
    connection.isPending
      ? { ok: undefined, text: "Checking your HMRC connection…" }
      : connection.isError
        ? { ok: false, text: "Couldn’t check your HMRC connection" }
        : connected
          ? { ok: true, text: "Connected to HMRC" }
          : { ok: false, text: "Not connected to HMRC" },
  ];
  if (connected)
    checks.push(
      taxpayer.isPending
        ? { ok: undefined, text: "Finding your details at HMRC…" }
        : taxpayer.isError
          ? { ok: false, text: "Couldn’t find your details at HMRC" }
          : business
            ? { ok: true, text: "National Insurance number and property business found" }
            : { ok: false, text: "No UK property business found at HMRC" },
    );
  const unsent = earlier.filter((x) => x.state.kind !== "sent");
  if (earlier.length > 0)
    checks.push(
      unsent.length === 0
        ? { ok: true, text: `${quarterNames(earlier)} already sent` }
        : {
            ok: undefined,
            text: `${quarterNames(unsent)} ${unsent.length === 1 ? "wasn’t" : "weren’t"} sent. This update covers ${unsent.length === 1 ? "it" : "them"} too.`,
          },
    );

  const sent = state === "sent" ? sentDetails(q, submissions) : undefined;

  return (
    <>
      <h2 id="send-heading" className={state === "overdue" ? s.overdueHeading : undefined}>
        {state === "sent" ? "Sent to HMRC" : state === "overdue" ? "Overdue" : "Ready to send"}
      </h2>
      {state === "overdue" && (
        <p className={s.prose}>
          It was due on {formatLong(q.deadline)}. Send it now to bring your record with HMRC up to
          date.
        </p>
      )}
      {sent && (
        <dl className={s.facts}>
          <dt>Sent</dt>
          <dd>
            {formatLong(sent.submission.submitted_at.slice(0, 10))}
            {sent.via !== q.quarter && <>, in the quarter {sent.via} update</>}
          </dd>
          {sent.submission.hmrc_correlation_id && (
            <>
              <dt>HMRC reference</dt>
              <dd className={s.reference}>{sent.submission.hmrc_correlation_id}</dd>
            </>
          )}
        </dl>
      )}
      <ul className={s.checks}>
        {checks.map((c) => (
          <li key={c.text} className={c.ok === false ? s.checkBad : undefined}>
            {c.ok === true ? (
              <CheckIcon size={18} />
            ) : c.ok === false ? (
              <AlertIcon size={18} />
            ) : (
              <span className={s.checkNeutral} aria-hidden="true" />
            )}
            {c.text}
          </li>
        ))}
      </ul>

      {connection.isSuccess && !connected ? (
        <ButtonLink to="/settings/hmrc" size="large" block>
          Connect to HMRC
        </ButtonLink>
      ) : canSend && state !== "sent" ? (
        <ButtonLink to={submitPath(year, q.quarter)} size="large" block>
          Review and submit
        </ButtonLink>
      ) : canSend && state === "sent" ? (
        <ButtonLink to={submitPath(year, q.quarter)} variant="secondary" block>
          Send again with updated figures
        </ButtonLink>
      ) : null}
      <p className={s.note}>
        If figures change after you’ve sent a quarter, you can send it again. Each submission is
        kept with HMRC’s reference.
      </p>
    </>
  );
}

interface Check {
  ok: boolean | undefined; // undefined: neither done nor a problem
  text: string;
}

/** "Quarter 1", "Quarters 1 and 2", "Quarters 1, 2 and 3". */
function quarterNames(quarters: Quarter[]): string {
  const n = quarters.map((x) => x.quarter);
  if (n.length === 1) return `Quarter ${n[0]}`;
  return `Quarters ${n.slice(0, -1).join(", ")} and ${n[n.length - 1]}`;
}

/** The accepted submission that covered this quarter: its own if there is one, latest first. */
function sentDetails(q: Quarter, submissions: Submission[]) {
  if (q.state.kind !== "sent") return undefined;
  const accepted = submissions.filter((x) => x.succeeded);
  const own = accepted
    .filter((x) => x.quarter === q.quarter)
    .sort((a, b) => b.submitted_at.localeCompare(a.submitted_at))[0];
  if (own) return { submission: own, via: q.quarter };
  const via = q.state.viaQuarter;
  const covering = accepted.find((x) => x.quarter === via);
  return covering ? { submission: covering, via } : undefined;
}

/* ---------- The figures ---------- */

interface Section {
  id: string;
  title: string;
  rows: CategoryAmount[];
  total?: { label: string; of: (t: TaxSummary["totals"]) => string };
  help?: string;
}

function sectionsOf(summary: TaxSummary): Section[] {
  const nonZero = summary.categories.filter((c) => toPence(c.amount) !== 0);
  const income = nonZero.filter((c) => c.kind === "income");
  const expenses = nonZero.filter((c) => c.kind === "expense" && c.category !== FINANCE);
  const finance = nonZero.filter((c) => c.category === FINANCE);
  const sections: Section[] = [
    {
      id: "income",
      title: "Income",
      rows: income,
      total: income.length > 1 ? { label: "Total income", of: (t) => t.income } : undefined,
    },
    {
      id: "expenses",
      title: "Expenses",
      rows: expenses,
      total: expenses.length > 1 ? { label: "Total expenses", of: (t) => t.expenses } : undefined,
    },
    {
      id: "separately",
      title: "Reported separately",
      rows: finance,
      help: "Mortgage interest. HMRC gives a tax credit for it rather than deducting it from your profit.",
    },
  ];
  return sections.filter((x) => x.rows.length > 0);
}

function Figures({
  summary,
  year,
  quarter,
}: {
  summary: TaxSummary;
  year: number;
  quarter: number;
}) {
  const wide = useMediaQuery(WIDE);
  const sections = sectionsOf(summary);
  const count = summary.properties.reduce((n, p) => n + p.transaction_count, 0);
  const transactions = `/transactions?period=${updatePeriodKey(year, quarter)}`;

  if (sections.length === 0)
    return (
      <p className={s.prose}>
        Nothing recorded between {formatLong(summary.period_start)} and{" "}
        {formatLong(summary.period_end)} yet. <Link to="/transactions/new">Add a transaction</Link>{" "}
        or <Link to="/transactions/import">import a bank statement</Link>.
      </p>
    );

  const byProperty = summary.properties.length > 1 && wide;
  return (
    <>
      {byProperty ? (
        <ByPropertyTable summary={summary} sections={sections} />
      ) : (
        <FigureList summary={summary} sections={sections} />
      )}
      <p className={s.note}>
        {byProperty
          ? "All figures are your share. "
          : `All figures are your share, ${whoseProperties(summary.properties.length)}. `}
        Categories with nothing in them aren’t sent.{" "}
        <Link to={transactions}>
          See the {count} {count === 1 ? "transaction" : "transactions"} behind these figures
        </Link>
      </p>
      {!byProperty && summary.properties.length > 1 && <PropertyBreakdown summary={summary} />}
    </>
  );
}

/** Phones, and anyone with one property: one column, as HMRC will receive it. */
function FigureList({ summary, sections }: { summary: TaxSummary; sections: Section[] }) {
  return (
    <div className={s.figureList}>
      {sections.map((sec) => (
        <section key={sec.id} aria-labelledby={`fig-${sec.id}`}>
          <h3 id={`fig-${sec.id}`}>{sec.title}</h3>
          <dl className={`${s.lines} num`}>
            {sec.rows.map((c) => (
              <div key={c.category}>
                <dt>{c.label}</dt>
                <dd>
                  <Amount pounds={c.amount} symbol={false} />
                </dd>
              </div>
            ))}
            {sec.total && (
              <div className={s.lineTotal}>
                <dt>{sec.total.label}</dt>
                <dd>
                  <Amount pounds={sec.total.of(summary.totals)} symbol={false} />
                </dd>
              </div>
            )}
          </dl>
          {sec.help && <p className={s.note}>{sec.help}</p>}
        </section>
      ))}
    </div>
  );
}

/** Tablets and up with more than one property: each property's share, then the total sent. */
function ByPropertyTable({ summary, sections }: { summary: TaxSummary; sections: Section[] }) {
  const props = summary.properties;
  const amount = (p: PropertySummary, category: string) =>
    p.categories.find((c) => c.category === category)?.amount ?? "0.00";
  const columns = props.length + 2;

  return (
    <div className={s.tableScroll}>
      <table className={`${s.figureTable} num`}>
        <caption className="visually-hidden">
          What HMRC will receive, by property, at your share
        </caption>
        <thead>
          <tr>
            <th scope="col">HMRC category</th>
            {props.map((p) => (
              <th scope="col" key={p.property_id} className={s.money}>
                {p.nickname}
                {!ownsAll(p.ownership_percentage) && (
                  <span className={s.colNote}> {trimPercentage(p.ownership_percentage)}%</span>
                )}
                {p.is_archived && <span className={s.colNote}> archived</span>}
              </th>
            ))}
            <th scope="col" className={s.money}>
              Total
            </th>
          </tr>
        </thead>
        {sections.map((sec) => (
          <tbody key={sec.id}>
            <tr className={s.groupRow}>
              <th scope="rowgroup" colSpan={columns}>
                {sec.title}
              </th>
            </tr>
            {sec.rows.map((c) => (
              <tr key={c.category}>
                <th scope="row">{c.label}</th>
                {props.map((p) => (
                  <td key={p.property_id} className={s.money}>
                    <Amount pounds={amount(p, c.category)} symbol={false} />
                  </td>
                ))}
                <td className={`${s.money} ${s.sum}`}>
                  <Amount pounds={c.amount} symbol={false} />
                </td>
              </tr>
            ))}
            {sec.total && (
              <tr className={s.totalRow}>
                <th scope="row">{sec.total.label}</th>
                {props.map((p) => (
                  <td key={p.property_id} className={s.money}>
                    <Amount pounds={sec.total!.of(p.totals)} symbol={false} />
                  </td>
                ))}
                <td className={s.money}>
                  <Amount pounds={sec.total.of(summary.totals)} symbol={false} />
                </td>
              </tr>
            )}
          </tbody>
        ))}
      </table>
    </div>
  );
}

/** On a phone, each property's part of the totals, folded away until asked for. */
function PropertyBreakdown({ summary }: { summary: TaxSummary }) {
  return (
    <details className={s.details}>
      <summary>By property</summary>
      <div className={s.detailsBody}>
        {summary.properties.map((p) => (
          <section key={p.property_id} aria-label={p.nickname}>
            <h3>
              {p.nickname}
              {!ownsAll(p.ownership_percentage) && (
                <span className={s.colNote}> your {trimPercentage(p.ownership_percentage)}%</span>
              )}
            </h3>
            <dl className={`${s.lines} num`}>
              <Line label="Income" pounds={p.totals.income} />
              <Line label="Expenses" pounds={p.totals.expenses} />
              {toPence(p.totals.residential_finance_costs) > 0 && (
                <Line
                  label="Residential finance costs"
                  pounds={p.totals.residential_finance_costs}
                />
              )}
            </dl>
          </section>
        ))}
      </div>
    </details>
  );
}

function Line({ label, pounds }: { label: ReactNode; pounds: string }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>
        <Amount pounds={pounds} symbol={false} />
      </dd>
    </div>
  );
}
