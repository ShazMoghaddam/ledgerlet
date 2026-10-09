import { Link } from "react-router";

import {
  useHmrcConnection,
  useMe,
  useObligations,
  useProperties,
  useSubmissions,
  useSummary,
  useTaxpayer,
  useTransactions,
} from "../../api/queries";
import type { Property, TaxSummary, TransactionItem } from "../../api/types";
import { Amount } from "../../components/Amount";
import { ButtonLink } from "../../components/Button";
import { LoadFailed, Loading } from "../../components/QueryState";
import { TaxYearRuler } from "../../components/TaxYearRuler";
import { WIDE, useMediaQuery } from "../../hooks/useMediaQuery";
import { usePageTitle } from "../../hooks/usePageTitle";
import { daysBetween, formatDayMonth, formatLong, formatShort, ukToday } from "../../lib/dates";
import { toPence } from "../../lib/money";
import { ownershipText, ownsAll } from "../../lib/ownership";
import {
  currentQuarter,
  nextStep,
  quarterStates,
  type NextStep,
  type Quarter,
} from "../../lib/quarters";
import s from "./OverviewPage.module.css";

export function OverviewPage({ today = ukToday() }: { today?: string }) {
  usePageTitle("Overview");
  const properties = useProperties();

  if (properties.isPending) return <Loading label="your overview" />;
  if (properties.isError)
    return <LoadFailed what="your overview" error={properties.error} retry={properties.refetch} />;
  if (properties.data.length === 0) return <FirstRun />;

  return (
    <div className={s.page}>
      <div className={s.main}>
        <YearAtAGlance today={today} properties={properties.data} />
      </div>
      {/* On laptops this is a column beside the page; below that it follows it. */}
      <aside className={s.aside} aria-label="Your account">
        <HmrcPanel />
        <PropertiesPanel properties={properties.data} />
      </aside>
    </div>
  );
}

function YearAtAGlance({ today, properties }: { today: string; properties: Property[] }) {
  const obligations = useObligations();
  const taxYear = obligations.data?.tax_year;
  const submissions = useSubmissions(taxYear);

  if (obligations.isError)
    return (
      <>
        <LoadFailed what="the tax year" error={obligations.error} retry={obligations.refetch} />
        <RecentTransactions properties={properties} />
      </>
    );
  if (obligations.isPending) return <Loading label="the tax year" />;

  // Which quarter has begun doesn't depend on HMRC, so the figures can show even
  // when HMRC can't be reached. Only "what's been sent" needs it.
  const dated = quarterStates(obligations.data.obligations, [], today);
  const current = currentQuarter(dated);

  return (
    <>
      {submissions.isError ? (
        <LoadFailed
          what="what you’ve sent to HMRC"
          error={submissions.error}
          retry={submissions.refetch}
        />
      ) : submissions.isPending ? (
        <Loading label="what you’ve sent to HMRC" />
      ) : (
        <SentAndDue
          today={today}
          taxYear={obligations.data.tax_year}
          label={`Tax year ${obligations.data.tax_year_label}`}
          quarters={quarterStates(obligations.data.obligations, submissions.data, today)}
        />
      )}
      <div className={s.columns}>
        <YearToDate
          taxYear={obligations.data.tax_year}
          quarter={current?.quarter}
          count={properties.length}
        />
        <RecentTransactions properties={properties} />
      </div>
    </>
  );
}

function SentAndDue({
  today,
  taxYear,
  label,
  quarters,
}: {
  today: string;
  taxYear: number;
  label: string;
  quarters: Quarter[];
}) {
  return (
    <>
      <NextStepHeadline step={nextStep(quarters)} today={today} taxYear={taxYear} />
      <TaxYearRuler quarters={quarters} today={today} label={label} />
    </>
  );
}

function NextStepHeadline({
  step,
  today,
  taxYear,
}: {
  step: NextStep;
  today: string;
  taxYear: number;
}) {
  if (step.kind === "year_done") {
    return (
      <section className={s.next} aria-labelledby="page-heading">
        <div className={s.nextText}>
          <h1 id="page-heading" tabIndex={-1}>
            This year’s updates are all sent
          </h1>
          <p>Next comes your final declaration for the year, after 5 April.</p>
        </div>
      </section>
    );
  }

  const q = step.quarter;
  if (step.kind === "wait") {
    const starting = q.state.kind === "not_started";
    return (
      <section className={s.next} aria-labelledby="page-heading">
        <div className={s.nextText}>
          <h1 id="page-heading" tabIndex={-1}>
            {starting
              ? `Quarter ${q.quarter} starts on ${formatShort(q.windowStart)}`
              : `Quarter ${q.quarter} is in progress`}
          </h1>
          <p>
            Keep recording income and expenses. It ends on {formatLong(q.windowEnd)} and is due by{" "}
            {formatLong(q.deadline)}.
          </p>
        </div>
        <ButtonLink to="/transactions/new" variant="secondary" size="large">
          Add transaction
        </ButtonLink>
      </section>
    );
  }

  const send = `/tax/${taxYear}/q${q.quarter}/submit`;
  return (
    <section className={s.next} aria-labelledby="page-heading">
      <div className={s.nextText}>
        {step.overdue ? (
          <>
            <h1 id="page-heading" tabIndex={-1} className={s.overdue}>
              Quarter {q.quarter} is overdue
            </h1>
            <p>
              It was due on {formatLong(q.deadline)}. Send it now to bring your record with HMRC up
              to date.
            </p>
          </>
        ) : (
          <>
            <h1 id="page-heading" tabIndex={-1}>
              Quarter {q.quarter} is ready to send
            </h1>
            <p>
              Your figures to {formatDayMonth(q.windowEnd)} are complete. HMRC needs them by{" "}
              {formatDayMonth(q.deadline)}, {dueIn(today, q.deadline)}.
            </p>
          </>
        )}
      </div>
      <ButtonLink to={send} size="large">
        Review and submit
      </ButtonLink>
    </section>
  );
}

function dueIn(today: string, deadline: string): string {
  const days = daysBetween(today, deadline);
  if (days <= 0) return "today";
  if (days === 1) return "tomorrow";
  return `in ${days} days`;
}

function YearToDate({
  taxYear,
  quarter,
  count,
}: {
  taxYear: number;
  quarter?: number;
  count: number;
}) {
  const summary = useSummary(taxYear, quarter);
  return (
    <section className={`${s.section} ${s.ytd}`} aria-labelledby="ytd-heading">
      <h2 id="ytd-heading">Year to date</h2>
      {summary.isPending ? (
        <Loading label="your figures" />
      ) : summary.isError ? (
        <LoadFailed what="your figures" error={summary.error} retry={summary.refetch} />
      ) : (
        <Statement summary={summary.data} count={count} />
      )}
    </section>
  );
}

function Statement({ summary, count }: { summary: TaxSummary; count: number }) {
  const t = summary.totals;
  const whose =
    count === 1 ? "your property" : count === 2 ? "both properties" : `all ${count} properties`;
  return (
    <>
      <dl className={`${s.statement} num`}>
        <div>
          <dt>Income</dt>
          <dd>
            <Amount pounds={t.income} />
          </dd>
        </div>
        <div>
          <dt>Expenses</dt>
          <dd>
            <Amount pounds={t.expenses} />
          </dd>
        </div>
        <div className={s.total}>
          <dt>Profit</dt>
          <dd>
            <Amount pounds={t.profit} />
          </dd>
        </div>
      </dl>
      <p className={s.note}>
        Your share across {whose}.
        {toPence(t.residential_finance_costs) > 0 && (
          <>
            {" "}
            Mortgage interest of <Amount pounds={t.residential_finance_costs} /> is reported
            separately, because HMRC gives a tax credit for it.
          </>
        )}
      </p>
    </>
  );
}

function RecentTransactions({ properties }: { properties: Property[] }) {
  const recent = useTransactions({ limit: 5 });
  const wide = useMediaQuery(WIDE);
  const byId = new Map(properties.map((p) => [p.id, p]));

  return (
    <section className={s.section} aria-labelledby="recent-heading">
      <div className={s.sectionHead}>
        <h2 id="recent-heading">Recent transactions</h2>
        <Link to="/transactions">All transactions</Link>
      </div>
      {recent.isPending ? (
        <Loading label="recent transactions" />
      ) : recent.isError ? (
        <LoadFailed what="recent transactions" error={recent.error} retry={recent.refetch} />
      ) : recent.data.items.length === 0 ? (
        <p className={s.note}>
          Nothing recorded yet. <Link to="/transactions/new">Add a transaction</Link> or{" "}
          <Link to="/transactions/import">import a bank statement</Link>.
        </p>
      ) : wide ? (
        <TransactionTable items={recent.data.items} byId={byId} />
      ) : (
        <TransactionList items={recent.data.items} byId={byId} />
      )}
    </section>
  );
}

type Lookup = Map<string, Property>;

/** Laptop and tablet: In and Out columns, so direction never depends on colour. */
function TransactionTable({ items, byId }: { items: TransactionItem[]; byId: Lookup }) {
  return (
    <table className={`${s.table} num`}>
      <caption className="visually-hidden">The five most recent transactions</caption>
      <thead>
        <tr>
          <th scope="col">Date</th>
          <th scope="col">Description</th>
          <th scope="col" className={s.money}>
            In
          </th>
          <th scope="col" className={s.money}>
            Out
          </th>
        </tr>
      </thead>
      <tbody>
        {items.map((t) => (
          <tr key={t.id}>
            <td className={s.date}>{formatShort(t.transaction_date)}</td>
            <td>
              {t.description} <span className={s.meta}>{byId.get(t.property_id)?.nickname}</span>
            </td>
            <td className={s.money}>
              {t.kind === "income" && <Amount pounds={t.amount} symbol={false} />}
            </td>
            <td className={s.money}>
              {t.kind === "expense" && <Amount pounds={t.amount} symbol={false} />}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

/** Phone: a list with signed amounts. */
function TransactionList({ items, byId }: { items: TransactionItem[]; byId: Lookup }) {
  return (
    <ul className={s.list}>
      {items.map((t) => {
        const prop = byId.get(t.property_id);
        const partShare = prop !== undefined && !ownsAll(prop.ownership_percentage);
        const signed = t.kind === "income" ? t.amount : `-${t.amount}`;
        return (
          <li key={t.id}>
            <span>
              {t.description}
              <span className={s.meta}>
                {formatShort(t.transaction_date)}, {prop?.nickname}
                {partShare && (
                  <>
                    . Your share <Amount pounds={t.share_amount} />
                  </>
                )}
              </span>
            </span>
            <Amount className={s.amount} pounds={signed} signed symbol={false} />
          </li>
        );
      })}
    </ul>
  );
}

function HmrcPanel() {
  const connection = useHmrcConnection();
  const taxpayer = useTaxpayer();
  const me = useMe();
  return (
    <section className={s.section} aria-labelledby="hmrc-heading">
      <h2 id="hmrc-heading">HMRC</h2>
      {connection.isPending ? (
        <Loading label="your HMRC connection" />
      ) : connection.isError ? (
        <LoadFailed
          what="your HMRC connection"
          error={connection.error}
          retry={connection.refetch}
        />
      ) : (
        <>
          <dl className={s.facts}>
            <dt>Status</dt>
            <dd>{connection.data.connected ? "Connected" : "Not connected"}</dd>
            {taxpayer.data?.nino && (
              <>
                <dt>NINO</dt>
                <dd className="num">{taxpayer.data.nino}</dd>
              </>
            )}
            <dt>Business</dt>
            <dd>{taxpayer.data?.uk_property_business_id ? "UK property" : "Not found yet"}</dd>
            {me.data && (
              <>
                <dt>Quarters</dt>
                <dd>
                  {me.data.period_basis === "calendar"
                    ? "Calendar, from 1 April"
                    : "Standard, from 6 April"}
                </dd>
              </>
            )}
          </dl>
          <Link className={s.strongLink} to="/settings/hmrc">
            {connection.data.connected ? "Manage connection" : "Connect to HMRC"}
          </Link>
        </>
      )}
    </section>
  );
}

function PropertiesPanel({ properties }: { properties: Property[] }) {
  const active = properties.filter((p) => !p.is_archived);
  return (
    <section className={s.section} aria-labelledby="properties-heading">
      <h2 id="properties-heading">Properties</h2>
      <ul className={s.properties}>
        {active.map((p) => (
          <li key={p.id}>
            <Link to={`/properties/${p.id}`}>{p.nickname}</Link>
            <span className={s.meta}>{ownershipText(p.ownership_percentage)}</span>
          </li>
        ))}
      </ul>
      <Link className={s.strongLink} to="/properties/new">
        Add a property
      </Link>
    </section>
  );
}

function FirstRun() {
  return (
    <section className={s.next} aria-labelledby="page-heading">
      <div className={s.nextText}>
        <h1 id="page-heading" tabIndex={-1}>
          Add your first property
        </h1>
        <p>
          LedgerLet works out what to send HMRC from the income and expenses of each property you
          let. Start with one; you can add more at any time.
        </p>
      </div>
      <ButtonLink to="/properties/new" size="large">
        Add a property
      </ButtonLink>
    </section>
  );
}
