import { useState } from "react";
import { Link, useLocation, useParams } from "react-router";

import { useProperty, useTransactions } from "../../api/queries";
import type { Property } from "../../api/types";
import { Amount } from "../../components/Amount";
import { Button, ButtonLink } from "../../components/Button";
import { Dialog } from "../../components/Dialog";
import { Notice } from "../../components/Notice";
import { LoadFailed, Loading } from "../../components/QueryState";
import { usePageTitle } from "../../hooks/usePageTitle";
import { formatLong, formatShort } from "../../lib/dates";
import { toPence } from "../../lib/money";
import { ownershipText, trimPercentage } from "../../lib/ownership";
import { BackLink } from "./BackLink";
import { useArchiveProperty } from "./mutations";
import s from "./Properties.module.css";
import { useYearFigures } from "./yearFigures";

/** /properties/:id: one property, its figures this year, and what can be done with it. */
export function PropertyPage() {
  const { id } = useParams();
  const property = useProperty(id);
  const notice = (useLocation().state as { notice?: string } | null)?.notice;
  usePageTitle(property.data?.nickname ?? "Property");

  if (property.isPending)
    return (
      <div className={s.page}>
        <BackLink to="/properties">All properties</BackLink>
        <h1 id="page-heading" tabIndex={-1}>
          Property
        </h1>
        <Loading label="the property" />
      </div>
    );
  if (property.isError)
    return (
      <div className={s.page}>
        <BackLink to="/properties">All properties</BackLink>
        <h1 id="page-heading" tabIndex={-1}>
          Property
        </h1>
        <LoadFailed what="the property" error={property.error} retry={property.refetch} />
      </div>
    );
  return <Details p={property.data} notice={notice} />;
}

function Details({ p, notice }: { p: Property; notice?: string }) {
  const share = trimPercentage(p.ownership_percentage);
  return (
    <div className={s.page}>
      <BackLink to="/properties">All properties</BackLink>
      {notice && <Notice>{notice}</Notice>}
      <div className={s.head}>
        <div className={s.headText}>
          <h1 id="page-heading" tabIndex={-1}>
            {p.nickname}
          </h1>
          {p.is_archived && (
            <p className={s.archivedTag}>
              Archived{p.archived_at && ` on ${formatLong(p.archived_at.slice(0, 10))}`}
            </p>
          )}
        </div>
        {!p.is_archived && (
          <div className={s.headActions}>
            <ButtonLink to={`/properties/${p.id}/edit`} variant="secondary">
              Edit<span className="visually-hidden"> {p.nickname}</span>
            </ButtonLink>
            <ButtonLink to={`/transactions/new?property=${p.id}`}>Add transaction</ButtonLink>
          </div>
        )}
      </div>

      <dl className={s.facts}>
        <div>
          <dt>Address</dt>
          <dd>
            {[p.address_line_1, p.address_line_2, p.town, p.postcode].filter(Boolean).join(", ")}
          </dd>
        </div>
        <div>
          <dt>Your share</dt>
          <dd>
            {ownershipText(p.ownership_percentage)}
            {share !== "100" && share !== "50" ? "" : ` (${share}%)`}
            <span className={s.meta}>
              Your part of its income and expenses for tax. LedgerLet works out every figure at this
              share.
            </span>
          </dd>
        </div>
      </dl>

      <ThisYear p={p} />
      <Recent p={p} />
      <ArchiveSection p={p} />
    </div>
  );
}

function ThisYear({ p }: { p: Property }) {
  const figures = useYearFigures();
  const mine = figures.byProperty.get(p.id);
  return (
    <section className={s.section} aria-labelledby="year-heading">
      <h2 id="year-heading">{figures.label ? `${figures.label} so far` : "This tax year"}</h2>
      {figures.error ? (
        <LoadFailed what="this year’s figures" error={figures.error} retry={figures.retry} />
      ) : figures.isPending ? (
        <Loading label="this year’s figures" />
      ) : (
        <>
          <dl className={`${s.lines} num`}>
            <div>
              <dt>Income</dt>
              <dd>
                <Amount pounds={mine?.totals.income ?? "0.00"} />
              </dd>
            </div>
            <div>
              <dt>Expenses</dt>
              <dd>
                <Amount pounds={mine?.totals.expenses ?? "0.00"} />
              </dd>
            </div>
            {mine && toPence(mine.totals.residential_finance_costs) > 0 && (
              <div>
                <dt>Mortgage interest</dt>
                <dd>
                  <Amount pounds={mine.totals.residential_finance_costs} />
                </dd>
              </div>
            )}
          </dl>
          <p className={s.note}>
            At your share, from {mine?.transaction_count ?? 0}{" "}
            {mine?.transaction_count === 1 ? "transaction" : "transactions"}.
          </p>
        </>
      )}
    </section>
  );
}

function Recent({ p }: { p: Property }) {
  const recent = useTransactions({ property_id: p.id, limit: 5 });
  return (
    <section className={s.section} aria-labelledby="recent-heading">
      <div className={s.sectionHead}>
        <h2 id="recent-heading">Recent transactions</h2>
        <Link to={`/transactions?property=${p.id}`}>
          All transactions<span className="visually-hidden"> for {p.nickname}</span>
        </Link>
      </div>
      {recent.isPending ? (
        <Loading label="recent transactions" />
      ) : recent.isError ? (
        <LoadFailed what="recent transactions" error={recent.error} retry={recent.refetch} />
      ) : recent.data.items.length === 0 ? (
        <p className={s.note}>
          Nothing recorded for {p.nickname} yet.
          {!p.is_archived && (
            <>
              {" "}
              <Link to={`/transactions/new?property=${p.id}`}>Add a transaction</Link> or{" "}
              <Link to={`/transactions/import?property=${p.id}`}>import a bank statement</Link>.
            </>
          )}
        </p>
      ) : (
        <ul className={s.recent}>
          {recent.data.items.map((t) => (
            <li key={t.id}>
              <Link to={`/transactions/${t.id}`}>{t.description}</Link>
              <span className={s.meta}>{formatShort(t.transaction_date)}</span>
              <Amount
                className={s.recentAmount}
                pounds={t.kind === "income" ? t.amount : `-${t.amount}`}
                signed
                symbol={false}
              />
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

/** Archive a property that's no longer let; restore one that is again. */
function ArchiveSection({ p }: { p: Property }) {
  const [open, setOpen] = useState(false);
  const archive = useArchiveProperty(p.id, !p.is_archived);

  if (p.is_archived)
    return (
      <section className={s.section} aria-labelledby="archive-heading">
        <h2 id="archive-heading">Letting it again?</h2>
        <p className={s.note}>Restoring it lets you add transactions to it and edit it again.</p>
        {archive.isError && (
          <p role="alert" className={s.problem}>
            {archive.error.message}
          </p>
        )}
        <div>
          <Button variant="secondary" disabled={archive.isPending} onClick={() => archive.mutate()}>
            {archive.isPending ? "Restoring…" : "Restore this property"}
          </Button>
        </div>
      </section>
    );

  return (
    <section className={s.section} aria-labelledby="archive-heading">
      <h2 id="archive-heading">No longer letting it?</h2>
      <p className={s.note}>
        Archive it once it’s sold or the letting has ended. Nothing is deleted.
      </p>
      <div>
        <Button variant="secondary" onClick={() => setOpen(true)}>
          Archive this property
        </Button>
      </div>
      <Dialog open={open} onClose={() => setOpen(false)} title={`Archive ${p.nickname}?`}>
        <p>
          Its transactions stay, and still count in this year’s figures for the dates they cover. It
          won’t appear when you add transactions or import a statement. You can restore it at any
          time.
        </p>
        {archive.isError && (
          <p role="alert" className={s.problem}>
            {archive.error.message}
          </p>
        )}
        <div className={s.dialogActions}>
          <Button
            variant="secondary"
            disabled={archive.isPending}
            onClick={() => archive.mutate(undefined, { onSuccess: () => setOpen(false) })}
          >
            {archive.isPending ? "Archiving…" : "Archive"}
          </Button>
          <Button variant="quiet" onClick={() => setOpen(false)}>
            Keep it
          </Button>
        </div>
      </Dialog>
    </section>
  );
}
