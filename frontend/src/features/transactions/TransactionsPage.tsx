import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useLocation, useParams } from "react-router";

import { useCategories, useObligations, useProperties, useTransactions } from "../../api/queries";
import type { Category, Property } from "../../api/types";
import { Amount } from "../../components/Amount";
import { Button, ButtonLink } from "../../components/Button";
import { Dialog } from "../../components/Dialog";
import f from "../../components/Field.module.css";
import { PlusIcon } from "../../components/Icons";
import { Notice } from "../../components/Notice";
import { LoadFailed, Loading } from "../../components/QueryState";
import { LAPTOP, WIDE, useMediaQuery } from "../../hooks/useMediaQuery";
import { usePageTitle } from "../../hooks/usePageTitle";
import { ukToday } from "../../lib/dates";
import { periodsFor, type Period } from "../../lib/periods";
import { PAGE_SIZE, useFilters, type Filters } from "./filters";
import { TransactionDetail } from "./TransactionDetail";
import { TransactionList, TransactionTable } from "./TransactionResults";
import s from "./TransactionsPage.module.css";

/**
 * /transactions and /transactions/:id. On a laptop the chosen transaction opens in a
 * panel beside the list; on a tablet or phone it gets the whole screen.
 */
export function TransactionsPage() {
  const { id } = useParams();
  const laptop = useMediaQuery(LAPTOP);
  const { search } = useFilters();
  const notice = (useLocation().state as { notice?: string } | null)?.notice;

  if (id && !laptop)
    return <TransactionDetail id={id} search={search} variant="page" notice={notice} />;
  return (
    <div className={`${s.layout} ${id ? s.withPanel : ""}`}>
      <TransactionsList selectedId={id} notice={id ? undefined : notice} />
      {id && <TransactionDetail key={id} id={id} search={search} variant="panel" notice={notice} />}
    </div>
  );
}

function TransactionsList({ selectedId, notice }: { selectedId?: string; notice?: string }) {
  usePageTitle("Transactions");
  const { filters, update, search } = useFilters();
  const obligations = useObligations();
  const properties = useProperties();
  const categories = useCategories();
  const today = ukToday();

  const periods = useMemo(
    () => (obligations.data ? periodsFor(obligations.data, today) : []),
    [obligations.data, today],
  );
  const period = periods.find((p) => p.key === filters.period) ?? periods[0];

  const results = useTransactions({
    limit: PAGE_SIZE,
    offset: (filters.page - 1) * PAGE_SIZE,
    date_from: period?.from,
    date_to: period?.to,
    property_id: filters.property,
    category: filters.category,
    q: filters.q,
  });

  return (
    <section
      className={`${s.list} ${selectedId ? s.compact : ""}`}
      aria-labelledby={selectedId ? "list-heading" : "page-heading"}
    >
      <div className={s.header}>
        <h1 id={selectedId ? "list-heading" : "page-heading"} tabIndex={-1}>
          Transactions
        </h1>
        <div className={s.actions}>
          <ButtonLink to="/transactions/import" variant="secondary">
            Import
          </ButtonLink>
          <ButtonLink
            to={`/transactions/new${filters.property ? `?property=${filters.property}` : ""}`}
          >
            <PlusIcon size={16} />
            Add
          </ButtonLink>
        </div>
      </div>

      {notice && <Notice>{notice}</Notice>}

      <FilterBar
        filters={filters}
        update={update}
        periods={periods}
        period={period}
        properties={properties.data ?? []}
        categories={categories.data ?? []}
      />

      {results.isPending || obligations.isPending ? (
        <Loading label="transactions" />
      ) : results.isError ? (
        <LoadFailed what="transactions" error={results.error} retry={results.refetch} />
      ) : (
        <Results
          page={results.data}
          filters={filters}
          properties={properties.data ?? []}
          search={search}
          selectedId={selectedId}
          filtered={Boolean(filters.property || filters.category || filters.q || filters.period)}
        />
      )}
    </section>
  );
}

function Results({
  page,
  filters,
  properties,
  search,
  selectedId,
  filtered,
}: {
  page: NonNullable<ReturnType<typeof useTransactions>["data"]>;
  filters: Filters;
  properties: Property[];
  search: string;
  selectedId?: string;
  filtered: boolean;
}) {
  const wide = useMediaQuery(WIDE);
  const laptop = useMediaQuery(LAPTOP);
  const byId = useMemo(() => new Map(properties.map((p) => [p.id, p])), [properties]);
  const one = filters.property ? byId.get(filters.property) : undefined;

  if (page.total === 0) {
    return filtered ? (
      <div className={s.empty}>
        <p>No transactions match these filters.</p>
        <Link to="/transactions">Clear filters</Link>
      </div>
    ) : (
      <div className={s.empty}>
        <p>Nothing recorded for this tax year yet.</p>
        <p>
          <Link to="/transactions/new">Add a transaction</Link> or{" "}
          <Link to="/transactions/import">import a bank statement</Link>.
        </p>
      </div>
    );
  }

  const first = page.offset + 1;
  const last = page.offset + page.items.length;
  const pageLink = (n: number) => {
    const params = new URLSearchParams(search);
    if (n > 1) params.set("page", String(n));
    else params.delete("page");
    const qs = params.toString();
    return `/transactions${qs ? `?${qs}` : ""}`;
  };

  return (
    <>
      <p className={`${s.summary} num`} aria-live="polite">
        {page.total} {page.total === 1 ? "transaction" : "transactions"}.{" "}
        {one ? `${one.nickname}, at your share` : "At your share"}: money in{" "}
        <strong>
          <Amount pounds={page.money_in} />
        </strong>
        , money out{" "}
        <strong>
          <Amount pounds={page.money_out} />
        </strong>
        .
      </p>

      {wide ? (
        <TransactionTable
          items={page.items}
          properties={byId}
          search={search}
          selectedId={selectedId}
          roomy={laptop && !selectedId}
        />
      ) : (
        <TransactionList items={page.items} properties={byId} search={search} />
      )}

      {page.total > PAGE_SIZE && (
        <nav className={s.pager} aria-label="Pages of transactions">
          <span className="num">
            Showing {first} to {last} of {page.total}
          </span>
          <div>
            {filters.page > 1 && <Link to={pageLink(filters.page - 1)}>Previous</Link>}
            {last < page.total && <Link to={pageLink(filters.page + 1)}>Next</Link>}
          </div>
        </nav>
      )}
    </>
  );
}

interface FilterBarProps {
  filters: Filters;
  update: ReturnType<typeof useFilters>["update"];
  periods: Period[];
  period?: Period;
  properties: Property[];
  categories: Category[];
}

/**
 * Search is always visible. The other filters sit inline on a laptop; on smaller
 * screens they're behind a Filters button, and what's applied shows as chips that
 * remove themselves when tapped.
 */
function FilterBar(props: FilterBarProps) {
  const { filters, update, period, properties, categories } = props;
  const [open, setOpen] = useState(false);
  const [text, setText] = useState(filters.q ?? "");

  // Search as you type, after a short pause; the URL stays the source of truth.
  useEffect(() => setText(filters.q ?? ""), [filters.q]);
  useEffect(() => {
    if (text === (filters.q ?? "")) return;
    const timer = setTimeout(() => update({ q: text.trim() || undefined }, { replace: true }), 300);
    return () => clearTimeout(timer);
  }, [text, filters.q, update]);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    update({ q: text.trim() || undefined }, { replace: true });
  };

  const property = properties.find((p) => p.id === filters.property);
  const category = categories.find((c) => c.value === filters.category);
  const applied = [filters.period, filters.property, filters.category].filter(Boolean).length;

  return (
    <>
      <form role="search" className={s.toolbar} onSubmit={submit}>
        <div className={s.search}>
          <label htmlFor="tx-search" className="visually-hidden">
            Search transactions
          </label>
          <div className={s.searchBox}>
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="var(--color-slate)"
              strokeWidth="1.9"
              aria-hidden="true"
            >
              <circle cx="11" cy="11" r="6" />
              <path d="M20 20l-4.5-4.5" />
            </svg>
            <input
              id="tx-search"
              type="search"
              value={text}
              placeholder="Description or amount"
              onChange={(e) => setText(e.target.value)}
              autoComplete="off"
            />
          </div>
        </div>
        <div className={s.inlineFilters}>
          <FilterFields {...props} idPrefix="inline" />
        </div>
        <Button variant="secondary" className={s.filtersButton} onClick={() => setOpen(true)}>
          Filters{applied > 0 && <span className="num"> ({applied})</span>}
        </Button>
      </form>

      <ul className={s.chips} aria-label="Filters applied">
        <li>
          <span className={s.fixedChip}>{period?.label ?? "This tax year"}</span>
        </li>
        {property && (
          <li>
            <Chip label={property.nickname} onRemove={() => update({ property: undefined })} />
          </li>
        )}
        {category && (
          <li>
            <Chip label={category.label} onRemove={() => update({ category: undefined })} />
          </li>
        )}
      </ul>

      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        title="Filter transactions"
        variant="sheet"
      >
        <div className={s.dialogFields}>
          <FilterFields {...props} idPrefix="sheet" />
        </div>
        <div className={s.dialogActions}>
          <Button onClick={() => setOpen(false)}>Show transactions</Button>
          {applied > 0 && (
            <Button
              variant="quiet"
              onClick={() =>
                update({ period: undefined, property: undefined, category: undefined })
              }
            >
              Clear filters
            </Button>
          )}
        </div>
      </Dialog>
    </>
  );
}

function Chip({ label, onRemove }: { label: string; onRemove: () => void }) {
  return (
    <button
      type="button"
      className={s.chip}
      onClick={onRemove}
      aria-label={`Remove filter: ${label}`}
    >
      {label}
      <svg
        width="12"
        height="12"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.8"
        aria-hidden="true"
      >
        <path d="M6 6l12 12M18 6L6 18" />
      </svg>
    </button>
  );
}

function FilterFields({
  filters,
  update,
  periods,
  period,
  properties,
  categories,
  idPrefix,
}: FilterBarProps & { idPrefix: string }) {
  return (
    <>
      <div className={f.field}>
        <label className={f.label} htmlFor={`${idPrefix}-period`}>
          Period
        </label>
        <select
          id={`${idPrefix}-period`}
          className={f.control}
          value={period?.key ?? ""}
          onChange={(e) =>
            update({ period: e.target.value === periods[0]?.key ? undefined : e.target.value })
          }
        >
          {periods.map((p) => (
            <option key={p.key} value={p.key}>
              {p.label}
            </option>
          ))}
        </select>
      </div>
      <div className={f.field}>
        <label className={f.label} htmlFor={`${idPrefix}-property`}>
          Property
        </label>
        <select
          id={`${idPrefix}-property`}
          className={f.control}
          value={filters.property ?? ""}
          onChange={(e) => update({ property: e.target.value || undefined })}
        >
          <option value="">All properties</option>
          {properties.map((p) => (
            <option key={p.id} value={p.id}>
              {p.nickname}
              {p.is_archived ? " (archived)" : ""}
            </option>
          ))}
        </select>
      </div>
      <div className={f.field}>
        <label className={f.label} htmlFor={`${idPrefix}-category`}>
          Category
        </label>
        <select
          id={`${idPrefix}-category`}
          className={f.control}
          value={filters.category ?? ""}
          onChange={(e) =>
            update({ category: (e.target.value || undefined) as Filters["category"] })
          }
        >
          <option value="">All categories</option>
          <optgroup label="Money in">
            {categories
              .filter((c) => c.kind === "income")
              .map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
          </optgroup>
          <optgroup label="Money out">
            {categories
              .filter((c) => c.kind === "expense")
              .map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
          </optgroup>
        </select>
      </div>
    </>
  );
}
