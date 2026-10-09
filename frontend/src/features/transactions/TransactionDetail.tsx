import { useState } from "react";
import { Link, useNavigate } from "react-router";

import {
  useCategories,
  useObligations,
  useProperties,
  useSubmissions,
  useTransaction,
} from "../../api/queries";
import type { TransactionItem } from "../../api/types";
import { Amount } from "../../components/Amount";
import { Button, ButtonLink } from "../../components/Button";
import { Dialog } from "../../components/Dialog";
import { Notice } from "../../components/Notice";
import { LoadFailed, Loading } from "../../components/QueryState";
import { usePageTitle } from "../../hooks/usePageTitle";
import { formatLong, formatShort, ukToday } from "../../lib/dates";
import { formatPounds } from "../../lib/money";
import { trimPercentage } from "../../lib/ownership";
import { quarterStates } from "../../lib/quarters";
import { useDeleteTransaction } from "./mutations";
import s from "./TransactionDetail.module.css";

const SOURCE: Record<TransactionItem["source"], string> = {
  manual: "Added by hand",
  csv_import: "Imported from a bank statement",
  open_banking: "From your bank",
};

/**
 * One transaction. "panel" sits beside the list on laptops; "page" stands alone on
 * tablets and phones. Either way the URL is /transactions/:id, so it can be linked to.
 */
export function TransactionDetail({
  id,
  search,
  variant,
  notice,
}: {
  id: string;
  search: string;
  variant: "panel" | "page";
  notice?: string;
}) {
  const transaction = useTransaction(id);
  const properties = useProperties();
  const categories = useCategories();
  usePageTitle(
    variant === "page" ? (transaction.data?.description ?? "Transaction") : "Transactions",
  );
  const back = `/transactions${search}`;
  const Heading = variant === "page" ? "h1" : "h2";

  const body = transaction.isPending ? (
    <Loading label="the transaction" />
  ) : transaction.isError ? (
    <LoadFailed what="this transaction" error={transaction.error} retry={transaction.refetch} />
  ) : (
    (() => {
      const t = transaction.data;
      const prop = properties.data?.find((p) => p.id === t.property_id);
      const label = categories.data?.find((c) => c.value === t.category)?.label;
      const pct = prop ? trimPercentage(prop.ownership_percentage) : undefined;
      return (
        <>
          <div className={s.head}>
            <div>
              <p className={s.context}>
                {formatLong(t.transaction_date)}
                {prop && `, ${prop.nickname}`}
              </p>
              <Heading id={variant === "page" ? "page-heading" : "detail-heading"} tabIndex={-1}>
                {t.description}
              </Heading>
            </div>
            {variant === "panel" && (
              <Link to={back} className={s.close} aria-label="Close details">
                <svg
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.2"
                  aria-hidden="true"
                >
                  <path d="M6 6l12 12M18 6L6 18" />
                </svg>
              </Link>
            )}
          </div>

          {notice && <Notice>{notice}</Notice>}

          <dl className={`${s.facts} num`}>
            <div>
              <dt>{t.kind === "income" ? "Amount received" : "Amount paid"}</dt>
              <dd>
                {formatPounds(t.amount)} {t.kind === "income" ? "in" : "out"}
              </dd>
            </div>
            {pct && pct !== "100" && (
              <div className={s.share}>
                <dt>Your share ({pct}%)</dt>
                <dd>
                  <Amount pounds={t.share_amount} />
                </dd>
              </div>
            )}
            <div>
              <dt>Category</dt>
              <dd>{label ?? t.category}</dd>
            </div>
            <CountsTowards date={t.transaction_date} />
            <div>
              <dt>Source</dt>
              <dd>{SOURCE[t.source]}</dd>
            </div>
          </dl>

          {t.is_locked ? (
            <p className={s.note}>
              This is part of a tax year already finalised with HMRC, so it can’t be changed. To
              correct it, record a new transaction.
            </p>
          ) : (
            <>
              <p className={s.note}>
                You can change this until the tax year is finalised. If it’s in a quarter you’ve
                already sent, your next update to HMRC includes the change.
              </p>
              <div className={s.actions}>
                <ButtonLink to={`/transactions/${t.id}/edit${search}`}>Edit</ButtonLink>
                <DeleteButton transaction={t} back={back} />
              </div>
            </>
          )}
        </>
      );
    })()
  );

  if (variant === "panel") {
    return (
      <aside className={`${s.detail} ${s.panel}`} aria-labelledby="detail-heading">
        {body}
      </aside>
    );
  }
  return (
    <div className={`${s.detail} ${s.page}`}>
      <Link to={back} className={s.back}>
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.2"
          aria-hidden="true"
        >
          <path d="M15 6l-6 6 6 6" />
        </svg>
        All transactions
      </Link>
      {body}
    </div>
  );
}

/** Which quarter this lands in, and whether that quarter has already gone to HMRC. */
function CountsTowards({ date }: { date: string }) {
  const obligations = useObligations();
  const submissions = useSubmissions(obligations.data?.tax_year);
  if (!obligations.data || !submissions.data) return null;
  const quarters = quarterStates(obligations.data.obligations, submissions.data, ukToday());
  const q = quarters.find((x) => x.windowStart <= date && date <= x.windowEnd);
  const text = !q
    ? "Another tax year"
    : q.state.kind === "sent"
      ? `Quarter ${q.quarter}, sent ${formatShort(q.state.on)}`
      : `Quarter ${q.quarter} ${obligations.data.tax_year_label}, not sent yet`;
  return (
    <div>
      <dt>Counts towards</dt>
      <dd>{text}</dd>
    </div>
  );
}

function DeleteButton({ transaction: t, back }: { transaction: TransactionItem; back: string }) {
  const [open, setOpen] = useState(false);
  const remove = useDeleteTransaction(t.id);
  const navigate = useNavigate();
  const direction = t.kind === "income" ? "in" : "out";

  return (
    <>
      <Button variant="secondary" className={s.danger} onClick={() => setOpen(true)}>
        Delete
      </Button>
      <Dialog open={open} onClose={() => setOpen(false)} title="Delete this transaction?">
        <p className={s.dialogText}>
          {t.description}, {formatPounds(t.amount)} {direction} on {formatLong(t.transaction_date)}.
          This can’t be undone.
        </p>
        {remove.isError && (
          <p role="alert" style={{ color: "var(--color-red)", fontWeight: 600 }}>
            {remove.error.message}
          </p>
        )}
        <div className={s.actions}>
          <Button
            className={s.danger}
            variant="secondary"
            disabled={remove.isPending}
            onClick={() =>
              remove.mutate(undefined, {
                onSuccess: () =>
                  navigate(back, { state: { notice: "Transaction deleted." }, replace: true }),
              })
            }
          >
            {remove.isPending ? "Deleting…" : "Delete transaction"}
          </Button>
          <Button variant="quiet" onClick={() => setOpen(false)}>
            Keep it
          </Button>
        </div>
      </Dialog>
    </>
  );
}
