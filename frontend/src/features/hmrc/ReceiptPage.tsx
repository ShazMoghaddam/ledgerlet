import { useState } from "react";
import { useParams } from "react-router";

import { useObligations, useSubmissions } from "../../api/queries";
import type { Submission } from "../../api/types";
import { Button, ButtonLink } from "../../components/Button";
import { CheckIcon } from "../../components/Icons";
import { LoadFailed, Loading } from "../../components/QueryState";
import { usePageTitle } from "../../hooks/usePageTitle";
import { formatLong, formatShort, ukToday } from "../../lib/dates";
import { formatPence } from "../../lib/money";
import { quarterStates } from "../../lib/quarters";
import { parseTaxPath, quarterPath, submitPath } from "../../lib/taxYear";
import { NotFoundPage } from "../placeholder/SectionPlaceholder";
import { sentFigures } from "./sentFigures";
import s from "./Submit.module.css";

const ukTime = new Intl.DateTimeFormat("en-GB", {
  timeZone: "Europe/London",
  hour: "2-digit",
  minute: "2-digit",
});
const ukDate = new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/London" });

/** /tax/2026/q2/receipt/<id>: one submission, as HMRC received it. Printable. */
export function ReceiptPage({ today = ukToday() }: { today?: string }) {
  const params = useParams();
  const { year } = parseTaxPath(params.year, params.quarter);
  if (year === undefined || !params.id) return <NotFoundPage />;
  return <Receipt year={year} id={params.id} today={today} />;
}

function Receipt({ year, id, today }: { year: number; id: string; today: string }) {
  usePageTitle("Submission receipt");
  const submissions = useSubmissions(year);

  if (submissions.isPending)
    return (
      <div className={s.page}>
        <h1 id="page-heading" tabIndex={-1}>
          Submission receipt
        </h1>
        <Loading label="the receipt" />
      </div>
    );
  if (submissions.isError)
    return (
      <div className={s.page}>
        <h1 id="page-heading" tabIndex={-1}>
          Submission receipt
        </h1>
        <LoadFailed what="the receipt" error={submissions.error} retry={submissions.refetch} />
      </div>
    );

  const sub = submissions.data.find((x) => x.id === id);
  if (!sub) return <NotFoundPage />;
  return sub.succeeded ? (
    <Accepted sub={sub} year={year} today={today} />
  ) : (
    <Refused sub={sub} year={year} />
  );
}

function sentAt(sub: Submission) {
  const when = new Date(sub.submitted_at);
  return `${formatLong(ukDate.format(when))} at ${ukTime.format(when)}`;
}

function Accepted({ sub, year, today }: { sub: Submission; year: number; today: string }) {
  const figures = sentFigures(sub.request_body);
  return (
    <div className={`${s.page} ${s.receipt}`}>
      <div className={s.accepted} role="status">
        <span className={s.acceptedMark} aria-hidden="true">
          <CheckIcon size={28} />
        </span>
        <h1 id="page-heading" tabIndex={-1}>
          HMRC has accepted your update
        </h1>
        <p className={s.lead}>
          Quarter {sub.quarter}, {formatShort(sub.period_start)} to {formatLong(sub.period_end)}.
          Sent {sentAt(sub)}.
        </p>
      </div>

      {sub.hmrc_correlation_id && <Reference value={sub.hmrc_correlation_id} />}

      <dl className={`${s.figures} num`}>
        <div>
          <dt>Income</dt>
          <dd>{formatPence(figures.income)}</dd>
        </div>
        <div>
          <dt>Expenses</dt>
          <dd>
            {formatPence(figures.expenses)}
            <span className={s.lineNote}>
              {" "}
              {figures.consolidated ? "as one total" : "by category"}
            </span>
          </dd>
        </div>
        <div>
          <dt>Residential finance costs</dt>
          <dd>{formatPence(figures.financeCosts)}</dd>
        </div>
        <div>
          <dt>Business</dt>
          <dd className="num">UK property, {sub.business_id}</dd>
        </div>
      </dl>

      <NextUp year={year} quarter={sub.quarter} today={today} />

      <div className={`${s.footer} ${s.noPrint}`}>
        <ButtonLink to="/" size="large">
          Back to overview
        </ButtonLink>
        <Button variant="secondary" onClick={() => window.print()}>
          Print or save this receipt
        </Button>
      </div>
    </div>
  );
}

function NextUp({ year, quarter, today }: { year: number; quarter: number; today: string }) {
  const obligations = useObligations(year);
  const quarters = obligations.data ? quarterStates(obligations.data.obligations, [], today) : [];
  const next = quarters.find((q) => q.quarter === quarter + 1);
  return (
    <p className={s.note}>
      {next
        ? `Next: quarter ${next.quarter} ends ${formatShort(next.windowEnd)} and is due ${formatShort(next.deadline)}. `
        : quarter === 4
          ? "That was the year’s last quarterly update. Next comes your final declaration. "
          : ""}
      If these figures change, your next update corrects them, because each one covers the tax year
      so far.
    </p>
  );
}

/** HMRC's reference, to quote if anyone asks. Copyable, and selectable for those who'd rather. */
function Reference({ value }: { value: string }) {
  const [copied, setCopied] = useState<boolean>();
  return (
    <div className={s.reference}>
      <span className={s.referenceLabel}>HMRC reference</span>
      <span className={s.referenceValue}>{value}</span>
      <Button
        variant="secondary"
        className={s.noPrint}
        onClick={async () => {
          try {
            await navigator.clipboard.writeText(value);
            setCopied(true);
          } catch {
            setCopied(false); // no clipboard access (an old browser, or permission refused)
          }
        }}
      >
        Copy reference
      </Button>
      <span role="status" className={s.copied}>
        {copied === true ? "Copied." : copied === false ? "Couldn’t copy. Select it instead." : ""}
      </span>
    </div>
  );
}

function Refused({ sub, year }: { sub: Submission; year: number }) {
  const body = sub.response_body as { code?: unknown; message?: unknown };
  return (
    <div className={s.page}>
      <div className={s.intro}>
        <h1 id="page-heading" tabIndex={-1}>
          HMRC didn’t accept this update
        </h1>
        <p className={s.lead}>
          Quarter {sub.quarter}, tried {sentAt(sub)}. Nothing changed at HMRC.
        </p>
      </div>
      <dl className={s.figures}>
        {typeof body.message === "string" && (
          <div>
            <dt>HMRC said</dt>
            <dd>{body.message}</dd>
          </div>
        )}
        {typeof body.code === "string" && (
          <div>
            <dt>Code</dt>
            <dd className="num">{body.code}</dd>
          </div>
        )}
        {sub.hmrc_correlation_id && (
          <div>
            <dt>HMRC reference</dt>
            <dd className={s.referenceValue}>{sub.hmrc_correlation_id}</dd>
          </div>
        )}
      </dl>
      <div className={s.footer}>
        <ButtonLink to={submitPath(year, sub.quarter)} size="large">
          Try again
        </ButtonLink>
        <ButtonLink to={quarterPath(year, sub.quarter)} variant="quiet">
          Back to quarter {sub.quarter}
        </ButtonLink>
      </div>
    </div>
  );
}
