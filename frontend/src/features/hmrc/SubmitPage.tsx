import { useRef, useState, type FormEvent, type ReactNode } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router";

import { ApiError } from "../../api/client";
import { useObligations, useSubmissions, useSummary, useTaxpayer } from "../../api/queries";
import type { TaxSummary } from "../../api/types";
import { Button, ButtonLink } from "../../components/Button";
import f from "../../components/Field.module.css";
import { LoadFailed, Loading } from "../../components/QueryState";
import { whoseProperties } from "../../components/Statement";
import { usePageTitle } from "../../hooks/usePageTitle";
import { formatDayMonth, formatLong, ukToday } from "../../lib/dates";
import { formatPence, toPence } from "../../lib/money";
import { updatePeriodKey } from "../../lib/periods";
import { quarterStates, type Quarter } from "../../lib/quarters";
import {
  FIRST_TAX_YEAR,
  parseTaxPath,
  quarterPath,
  receiptPath,
  submitPath,
  taxYearOf,
} from "../../lib/taxYear";
import { NotFoundPage } from "../notFound/NotFoundPage";
import { Checklist } from "../tax/Checklist";
import { NoProperties, useHasNoProperties } from "../tax/NoProperties";
import { hmrcSettingsPath, useReadiness } from "../tax/readiness";
import { usePreviewUpdate, useSendUpdate } from "./mutations";
import { sentFigures } from "./sentFigures";
import s from "./Submit.module.css";

/** HMRC lets expenses go as one total while property income is under £90,000. */
const CONSOLIDATED_LIMIT_PENCE = 90_000_00;

type Step = "check" | "expenses" | "confirm";
const STEP_NAMES: Record<Step, string> = { check: "Check", expenses: "Expenses", confirm: "Send" };

/**
 * /tax/2026/q2/submit, /submit/expenses, /submit/confirm. Each step is its own
 * address, so Back works and focus moves to the new heading. The expenses choice
 * travels in the address too (?expenses=total). Nothing is sent until the last step.
 */
export function SubmitPage({ today = ukToday() }: { today?: string }) {
  const params = useParams();
  const { year, quarter } = parseTaxPath(params.year, params.quarter);
  const step = params.step ?? "check";
  if (
    year === undefined ||
    quarter === undefined ||
    year < FIRST_TAX_YEAR ||
    year > taxYearOf(today) ||
    !["check", "expenses", "confirm"].includes(step)
  )
    return <NotFoundPage />;
  return <Submit year={year} quarter={quarter} step={step as Step} today={today} />;
}

function Submit({
  year,
  quarter,
  step,
  today,
}: {
  year: number;
  quarter: number;
  step: Step;
  today: string;
}) {
  usePageTitle(`Send quarter ${quarter}`);
  const obligations = useObligations(year);
  const submissions = useSubmissions(year);
  const summary = useSummary(year, quarter);
  const noProperties = useHasNoProperties();

  if (noProperties)
    return (
      <Frame year={year} quarter={quarter}>
        <h1 id="page-heading" tabIndex={-1}>
          Send quarter {quarter}
        </h1>
        <NoProperties />
      </Frame>
    );

  const failed = [obligations, submissions, summary].find((x) => x.isError);
  if (failed)
    return (
      <Frame year={year} quarter={quarter}>
        <h1 id="page-heading" tabIndex={-1}>
          Send quarter {quarter}
        </h1>
        <LoadFailed what="this quarter" error={failed.error} retry={failed.refetch} />
      </Frame>
    );
  if (!obligations.data || !submissions.data || !summary.data)
    return (
      <Frame year={year} quarter={quarter}>
        <h1 id="page-heading" tabIndex={-1}>
          Send quarter {quarter}
        </h1>
        <Loading label="this quarter" />
      </Frame>
    );

  const quarters = quarterStates(obligations.data.obligations, submissions.data, today);
  const q = quarters.find((x) => x.quarter === quarter);
  if (!q) return <NotFoundPage />;
  return (
    <Ready
      year={year}
      q={q}
      earlier={quarters.filter((x) => x.quarter < quarter)}
      summary={summary.data}
      step={step}
      today={today}
    />
  );
}

/** The page around every step: a way back out, and nothing else to distract. */
function Frame({
  year,
  quarter,
  back,
  children,
}: {
  year: number;
  quarter: number;
  back?: { to: string; label: string };
  children: ReactNode;
}) {
  return (
    <div className={s.page}>
      <nav aria-label="Leave or go back" className={s.topLinks}>
        {back ? <Link to={back.to}>{back.label}</Link> : <span />}
        <Link to={quarterPath(year, quarter)}>
          Exit<span className="visually-hidden"> sending quarter {quarter}</span>
        </Link>
      </nav>
      {children}
    </div>
  );
}

function Ready({
  year,
  q,
  earlier,
  summary,
  step,
  today,
}: {
  year: number;
  q: Quarter;
  earlier: Quarter[];
  summary: TaxSummary;
  step: Step;
  today: string;
}) {
  const [search] = useSearchParams();
  const { checks, blocker } = useReadiness(q, earlier, today);
  const canConsolidate = toPence(summary.totals.income) < CONSOLIDATED_LIMIT_PENCE;
  const consolidated = canConsolidate && search.get("expenses") === "total";
  const steps: Step[] = canConsolidate ? ["check", "expenses", "confirm"] : ["check", "confirm"];
  const base = submitPath(year, q.quarter);
  const query = consolidated ? "?expenses=total" : "";
  const pathOf = (x: Step) => `${base}${x === "check" ? "" : `/${x}`}${query}`;

  if (blocker === "checking")
    return (
      <Frame year={year} quarter={q.quarter}>
        <h1 id="page-heading" tabIndex={-1}>
          Send quarter {q.quarter}
        </h1>
        <Loading label="your HMRC connection" />
      </Frame>
    );
  if (blocker)
    return (
      <Frame year={year} quarter={q.quarter}>
        <h1 id="page-heading" tabIndex={-1}>
          Quarter {q.quarter} can’t be sent yet
        </h1>
        <Checklist checks={checks} />
        {blocker === "connect" || blocker === "details" ? (
          <div>
            <ButtonLink to={hmrcSettingsPath(base)} size="large">
              {blocker === "connect" ? "Connect to HMRC" : "Add your HMRC details"}
            </ButtonLink>
          </div>
        ) : blocker === "not_ended" ? (
          <p className={s.prose}>
            It can be sent once the quarter ends on {formatLong(q.windowEnd)}.
          </p>
        ) : (
          <p className={s.prose}>Try again in a moment.</p>
        )}
      </Frame>
    );

  // A step that doesn't apply (expenses when income is £90,000 or more) starts over.
  const current = steps.includes(step) ? step : "check";
  const index = steps.indexOf(current);
  const previous = steps[index - 1];
  const nextStep = steps[index + 1];
  const back = previous
    ? { to: pathOf(previous), label: "Back" }
    : { to: quarterPath(year, q.quarter), label: `Quarter ${q.quarter}` };

  return (
    <Frame year={year} quarter={q.quarter} back={back}>
      <StepBar steps={steps} current={current} />
      {current === "check" && (
        <CheckStep
          summary={summary}
          year={year}
          quarter={q.quarter}
          next={pathOf(nextStep ?? "confirm")}
        />
      )}
      {current === "expenses" && (
        <ExpensesStep
          summary={summary}
          consolidated={consolidated}
          next={(total) => `${base}/confirm${total ? "?expenses=total" : ""}`}
        />
      )}
      {current === "confirm" && <ConfirmStep year={year} q={q} consolidated={consolidated} />}
    </Frame>
  );
}

function StepBar({ steps, current }: { steps: Step[]; current: Step }) {
  const index = steps.indexOf(current);
  return (
    <div className={s.stepBar}>
      <p className={s.stepCount}>
        Step {index + 1} of {steps.length}
      </p>
      <ol className={s.steps} aria-hidden="true">
        {steps.map((x, i) => (
          <li key={x} className={i < index ? s.done : i === index ? s.now : undefined}>
            {STEP_NAMES[x]}
          </li>
        ))}
      </ol>
    </div>
  );
}

/* ---------- Step 1: are the figures right? ---------- */

function CheckStep({
  summary,
  year,
  quarter,
  next,
}: {
  summary: TaxSummary;
  year: number;
  quarter: number;
  next: string;
}) {
  const navigate = useNavigate();
  const t = summary.totals;
  const count = summary.properties.reduce((n, p) => n + p.transaction_count, 0);
  const nonZero = summary.categories.filter((c) => toPence(c.amount) !== 0);

  return (
    <>
      <div className={s.intro}>
        <h1 id="page-heading" tabIndex={-1}>
          Check your figures
        </h1>
        <p className={s.lead}>
          Totals from {formatDayMonth(summary.period_start)} to {formatLong(summary.period_end)}, at
          your share of {whoseProperties(summary.properties.length)}.
        </p>
      </div>
      <dl className={`${s.figures} num`}>
        <Line label="Income" pence={toPence(t.income)} />
        <Line label="Expenses" pence={toPence(t.expenses)} />
        <Line label="Residential finance costs" pence={toPence(t.residential_finance_costs)} />
      </dl>
      <details className={s.details}>
        <summary>Show by HMRC category</summary>
        <dl className={`${s.figures} ${s.small} num`}>
          {nonZero.map((c) => (
            <Line key={c.category} label={c.label} pence={toPence(c.amount)} />
          ))}
        </dl>
      </details>
      <div className={s.aside}>
        <p>
          Includes {count} {count === 1 ? "transaction" : "transactions"}. If something is missing
          or wrong, fix it first, then come back to this step.
        </p>
        <Link to={`/transactions?period=${updatePeriodKey(year, quarter)}`}>
          Review transactions
        </Link>
      </div>
      <div className={s.footer}>
        <Button size="large" onClick={() => navigate(next)}>
          These figures are right
        </Button>
      </div>
    </>
  );
}

/* ---------- Step 2: by category, or one total? ---------- */

function ExpensesStep({
  summary,
  consolidated,
  next,
}: {
  summary: TaxSummary;
  consolidated: boolean;
  next: (total: boolean) => string;
}) {
  const navigate = useNavigate();
  const [total, setTotal] = useState(consolidated);
  const expenses = toPence(summary.totals.expenses);
  const categories = summary.categories.filter(
    (c) =>
      c.kind === "expense" && c.category !== "residential_finance_costs" && toPence(c.amount) !== 0,
  ).length;
  const finance = toPence(summary.totals.residential_finance_costs);

  return (
    <form
      className={s.form}
      onSubmit={(e) => {
        e.preventDefault();
        navigate(next(total));
      }}
    >
      <fieldset className={s.fieldset}>
        <legend>
          <h1 id="page-heading" tabIndex={-1}>
            How should expenses be sent?
          </h1>
        </legend>
        <p className={s.lead}>
          Your property income this year is under £90,000 so far, so HMRC lets you send one total
          instead of each category.
        </p>
        <div className={s.options}>
          <div className={s.option}>
            <input
              id="expenses-itemised"
              type="radio"
              name="expenses"
              checked={!total}
              onChange={() => setTotal(false)}
              aria-describedby="expenses-itemised-text"
            />
            <div className={s.optionBody}>
              <label htmlFor="expenses-itemised" className={s.optionLabel}>
                By category
              </label>
              <span id="expenses-itemised-text" className={s.optionText}>
                {categories} {categories === 1 ? "category" : "categories"}, {formatPence(expenses)}{" "}
                in total. Matches your records exactly. Recommended.
              </span>
            </div>
          </div>
          <div className={s.option}>
            <input
              id="expenses-total"
              type="radio"
              name="expenses"
              checked={total}
              onChange={() => setTotal(true)}
              aria-describedby="expenses-total-text"
            />
            <div className={s.optionBody}>
              <label htmlFor="expenses-total" className={s.optionLabel}>
                One total
              </label>
              <span id="expenses-total-text" className={s.optionText}>
                {formatPence(expenses)} as consolidated expenses.
              </span>
            </div>
          </div>
        </div>
      </fieldset>
      {finance > 0 && (
        <p className={s.note}>
          Residential finance costs of {formatPence(finance)} are always sent on their own,
          whichever you choose.
        </p>
      )}
      <div className={s.footer}>
        <Button type="submit" size="large">
          Continue
        </Button>
      </div>
    </form>
  );
}

/* ---------- Step 3: confirm, and send ---------- */

function ConfirmStep({
  year,
  q,
  consolidated,
}: {
  year: number;
  q: Quarter;
  consolidated: boolean;
}) {
  const navigate = useNavigate();
  const preview = usePreviewUpdate({ taxYear: year, quarter: q.quarter, consolidated });
  const taxpayer = useTaxpayer();
  const send = useSendUpdate();
  const [confirmed, setConfirmed] = useState(false);
  const [unticked, setUnticked] = useState(false);
  const box = useRef<HTMLInputElement>(null);

  function submit(e: FormEvent) {
    e.preventDefault();
    if (!confirmed) {
      setUnticked(true);
      box.current?.focus();
      return;
    }
    send.mutate(
      { taxYear: year, quarter: q.quarter, consolidated },
      {
        // Replace this step in the history, so Back from the receipt can't resend.
        onSuccess: (sub) => navigate(receiptPath(year, q.quarter, sub.id), { replace: true }),
      },
    );
  }

  const business = taxpayer.data?.uk_property_business_id;
  const figures = preview.data ? sentFigures(preview.data.body) : undefined;

  return (
    <form className={s.form} onSubmit={submit} noValidate>
      <div className={s.intro}>
        <h1 id="page-heading" tabIndex={-1}>
          Confirm and send to HMRC
        </h1>
        <p className={s.lead}>
          This is exactly what HMRC will receive for your UK property business.
        </p>
      </div>

      {preview.isPending ? (
        <Loading label="what will be sent" />
      ) : preview.isError ? (
        <LoadFailed what="what will be sent" error={preview.error} retry={preview.refetch} />
      ) : (
        figures && (
          <>
            <dl className={`${s.figures} num`}>
              <div>
                <dt>Period</dt>
                <dd>
                  {formatDayMonth(preview.data.period_start)} to{" "}
                  {formatLong(preview.data.period_end)}
                </dd>
              </div>
              {business && (
                <div>
                  <dt>Business</dt>
                  <dd>UK property, {shortId(business)}</dd>
                </div>
              )}
              <Line label="Income" pence={figures.income} />
              <Line
                label="Expenses"
                pence={figures.expenses}
                note={figures.consolidated ? "as one total" : "by category"}
              />
              <Line label="Residential finance costs" pence={figures.financeCosts} />
            </dl>
            <details className={s.details}>
              <summary>See the data sent to HMRC</summary>
              {/* eslint-disable-next-line jsx-a11y/no-noninteractive-tabindex -- scrollable, so keyboard users can scroll it */}
              <pre className={s.json} tabIndex={0} aria-label="The data sent to HMRC">
                {JSON.stringify(preview.data.body, null, 2)}
              </pre>
            </details>
          </>
        )
      )}

      <div className={`${f.field} ${unticked && !confirmed ? f.hasError : ""} ${s.confirmField}`}>
        {unticked && !confirmed && (
          <span id="confirm-error" className={f.error}>
            Tick the box to confirm the figures before sending
          </span>
        )}
        <label className={`${s.tick} ${confirmed ? s.ticked : ""}`}>
          <input
            ref={box}
            type="checkbox"
            checked={confirmed}
            onChange={(e) => setConfirmed(e.target.checked)}
            aria-invalid={unticked && !confirmed ? true : undefined}
            aria-describedby={unticked && !confirmed ? "confirm-error" : undefined}
          />
          <span>I confirm these figures are correct and complete to the best of my knowledge.</span>
        </label>
      </div>
      <p className={s.note}>
        If figures change later, your next quarterly update corrects them, because each one covers
        the tax year so far. You can also send this quarter again.
      </p>

      {send.isError && <SendFailed error={send.error} year={year} quarter={q.quarter} />}

      <div className={s.footer}>
        <Button type="submit" size="large" disabled={send.isPending || !preview.isSuccess}>
          {send.isPending ? "Sending to HMRC…" : "Send to HMRC"}
        </Button>
      </div>
    </form>
  );
}

/** What went wrong, in terms of what the landlord should do next. */
function SendFailed({ error, year, quarter }: { error: Error; year: number; quarter: number }) {
  if (!(error instanceof ApiError))
    return (
      <div role="alert" className={s.problem}>
        <strong>LedgerLet couldn’t confirm whether it was sent.</strong>
        <p>
          The connection dropped before HMRC’s answer arrived. Check{" "}
          <Link to={quarterPath(year, quarter)}>the quarter’s status</Link> before trying again.
        </p>
      </div>
    );
  if (error.status === 409)
    return (
      <div role="alert" className={s.problem}>
        <strong>Nothing was sent.</strong>
        <p>
          {error.message}{" "}
          <Link to={hmrcSettingsPath(submitPath(year, quarter) + "/confirm")}>
            Check your HMRC connection
          </Link>
        </p>
      </div>
    );
  if (error.status === 502)
    return (
      <div role="alert" className={s.problem}>
        <strong>HMRC didn’t accept the update.</strong>
        <p>{error.message}</p>
        <p>Nothing has changed at HMRC. This attempt is kept in your submission history.</p>
      </div>
    );
  return (
    <div role="alert" className={s.problem}>
      <strong>Nothing was sent.</strong>
      <p>{error.message}</p>
    </div>
  );
}

function Line({ label, pence, note }: { label: string; pence: number; note?: string }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>
        <span className={s.amount}>{formatPence(pence)}</span>
        {note && <span className={s.lineNote}> {note}</span>}
      </dd>
    </div>
  );
}

/** "XDIS…6364": enough to recognise, without the whole id. */
const shortId = (id: string) => (id.length > 10 ? `${id.slice(0, 4)}…${id.slice(-4)}` : id);
