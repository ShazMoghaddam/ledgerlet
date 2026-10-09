import { useState, type FormEvent } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router";

import { ApiError } from "../../api/client";
import { useCategories, useProperties, useTransaction } from "../../api/queries";
import type { Category, Property, TransactionCategory, TransactionItem } from "../../api/types";
import { Button } from "../../components/Button";
import { ErrorSummary, type FieldError } from "../../components/ErrorSummary";
import f from "../../components/Field.module.css";
import { LoadFailed, Loading } from "../../components/QueryState";
import { usePageTitle } from "../../hooks/usePageTitle";
import { CATEGORY_HELP } from "../../lib/categories";
import { ukToday } from "../../lib/dates";
import { parseAmountInput, toApiAmount } from "../../lib/money";
import { ownsAll, trimPercentage } from "../../lib/ownership";
import { useCreateTransaction, useUpdateTransaction, type TransactionFields } from "./mutations";
import s from "./TransactionForm.module.css";

type Kind = "income" | "expense";

interface Values {
  propertyId: string;
  kind: Kind | "";
  category: TransactionCategory | "";
  date: string;
  description: string;
  amount: string;
}

/** /transactions/new: a blank form, with property and direction from the URL if given. */
export function NewTransactionPage() {
  usePageTitle("Add a transaction");
  const [params] = useSearchParams();
  const properties = useProperties();
  const categories = useCategories();
  if (properties.isPending || categories.isPending) return <Loading label="the form" />;
  if (properties.isError)
    return (
      <LoadFailed what="your properties" error={properties.error} retry={properties.refetch} />
    );
  if (categories.isError)
    return <LoadFailed what="the categories" error={categories.error} retry={categories.refetch} />;

  const active = properties.data.filter((p) => !p.is_archived);
  if (active.length === 0) {
    return (
      <div className={s.page}>
        <h1 id="page-heading" tabIndex={-1}>
          Add a transaction
        </h1>
        <p>
          Transactions belong to a property. <Link to="/properties/new">Add a property</Link> first.
        </p>
      </div>
    );
  }
  const wanted = params.get("property");
  const kind = params.get("kind");
  return (
    <TransactionForm
      properties={active}
      categories={categories.data}
      initial={{
        propertyId:
          active.find((p) => p.id === wanted)?.id ?? (active.length === 1 ? active[0]!.id : ""),
        kind: kind === "income" || kind === "expense" ? kind : "",
        category: "",
        date: ukToday(),
        description: "",
        amount: "",
      }}
    />
  );
}

/** /transactions/:id/edit: the same form, filled in. The property can't change. */
export function EditTransactionPage() {
  usePageTitle("Edit transaction");
  const { id = "" } = useParams();
  const transaction = useTransaction(id);
  const properties = useProperties();
  const categories = useCategories();
  if (transaction.isPending || properties.isPending || categories.isPending)
    return <Loading label="the transaction" />;
  if (transaction.isError)
    return (
      <LoadFailed what="this transaction" error={transaction.error} retry={transaction.refetch} />
    );
  if (properties.isError || categories.isError)
    return <LoadFailed what="the form" error={properties.error ?? categories.error} />;

  const t = transaction.data;
  if (t.is_locked) {
    return (
      <div className={s.page}>
        <h1 id="page-heading" tabIndex={-1}>
          This transaction can’t be changed
        </h1>
        <p>
          It’s part of a tax year already finalised with HMRC. To correct it, record a new
          transaction.
        </p>
        <Link to={`/transactions/${t.id}`}>Back to the transaction</Link>
      </div>
    );
  }
  return (
    <TransactionForm
      existing={t}
      properties={properties.data}
      categories={categories.data}
      initial={{
        propertyId: t.property_id,
        kind: t.kind,
        category: t.category,
        date: t.transaction_date,
        description: t.description,
        amount: t.amount,
      }}
    />
  );
}

function TransactionForm({
  existing,
  properties,
  categories,
  initial,
}: {
  existing?: TransactionItem;
  properties: Property[];
  categories: Category[];
  initial: Values;
}) {
  const navigate = useNavigate();
  const [search] = useSearchParams();
  const [values, setValues] = useState<Values>(initial);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [summary, setSummary] = useState<FieldError[]>([]);
  const create = useCreateTransaction();
  const updateTx = useUpdateTransaction(existing?.id ?? "");
  const saving = create.isPending || updateTx.isPending;
  const today = ukToday();

  const set = <K extends keyof Values>(key: K, value: Values[K]) =>
    setValues((v) => ({ ...v, [key]: value, ...(key === "kind" ? { category: "" } : {}) }));

  const property = properties.find((p) => p.id === values.propertyId);
  const shown = categories.filter((c) => c.kind === values.kind);
  const back = existing ? `/transactions/${existing.id}` : `/transactions`;

  function validate(): { fields: TransactionFields; propertyId: string } | null {
    const found: Record<string, string> = {};
    if (!values.propertyId) found["tx-property"] = "Choose the property this is for";
    if (!values.kind) found["tx-kind-income"] = "Choose money in or money out";
    else if (!values.category) found["tx-category"] = "Choose a category";
    if (!values.date) found["tx-date"] = "Enter the date";
    else if (values.date > today) found["tx-date"] = "The date can’t be in the future";
    if (!values.description.trim())
      found["tx-description"] = "Enter a description, like “October rent”";
    else if (values.description.trim().length > 255)
      found["tx-description"] = "Keep the description to 255 characters or fewer";
    const amount = parseAmountInput(values.amount);
    if (!amount.ok) found["tx-amount"] = amount.error;

    setErrors(found);
    setSummary(Object.entries(found).map(([field, message]) => ({ field, message })));
    if (Object.keys(found).length || !amount.ok) return null;
    return {
      propertyId: values.propertyId,
      fields: {
        transaction_date: values.date,
        category: values.category as TransactionCategory,
        description: values.description.trim(),
        amount: toApiAmount(amount.pence),
      },
    };
  }

  function submit(e: FormEvent) {
    e.preventDefault();
    const ok = validate();
    if (!ok) return;
    const onError = (error: Error) =>
      setSummary([
        {
          message:
            error instanceof ApiError
              ? error.message
              : "Couldn’t save. Check your connection and try again.",
        },
      ]);
    const keep = search.toString() ? `?${search.toString()}` : "";
    if (existing) {
      updateTx.mutate(ok.fields, {
        onSuccess: () =>
          navigate(`/transactions/${existing.id}${keep}`, { state: { notice: "Changes saved." } }),
        onError,
      });
    } else {
      create.mutate(ok, {
        onSuccess: (created) =>
          navigate(`/transactions/${created.id}`, { state: { notice: "Transaction added." } }),
        onError,
      });
    }
  }

  const err = (id: string) =>
    errors[id] ? (
      <span id={`${id}-error`} className={f.error}>
        <span className="visually-hidden">Error: </span>
        {errors[id]}
      </span>
    ) : null;
  const describedBy = (...ids: (string | false)[]) => ids.filter(Boolean).join(" ") || undefined;
  const partShare = property && !ownsAll(property.ownership_percentage);

  return (
    <div className={s.page}>
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
        {existing ? "Back to the transaction" : "All transactions"}
      </Link>
      <h1 id="page-heading" tabIndex={-1}>
        {existing ? "Edit transaction" : "Add a transaction"}
      </h1>

      <ErrorSummary errors={summary} />

      <form className={s.form} onSubmit={submit} noValidate>
        {existing ? (
          <dl className={s.readonly}>
            <dt>Property</dt>
            <dd>{property?.nickname}. A transaction stays with its property.</dd>
          </dl>
        ) : (
          <div className={`${f.field} ${errors["tx-property"] ? f.hasError : ""}`}>
            <label className={f.label} htmlFor="tx-property">
              Property
            </label>
            {err("tx-property")}
            <select
              id="tx-property"
              className={f.control}
              value={values.propertyId}
              onChange={(e) => set("propertyId", e.target.value)}
              aria-invalid={errors["tx-property"] ? true : undefined}
              aria-describedby={describedBy(
                errors["tx-property"] !== undefined && "tx-property-error",
              )}
            >
              <option value="">Choose a property</option>
              {properties.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.nickname}
                </option>
              ))}
            </select>
          </div>
        )}

        <fieldset
          className={`${f.choices} ${errors["tx-kind-income"] ? f.hasError : ""}`}
          aria-describedby={describedBy(
            errors["tx-kind-income"] !== undefined && "tx-kind-income-error",
          )}
        >
          <legend>Money in or out?</legend>
          {err("tx-kind-income")}
          <div className={f.options}>
            <label className={f.choice}>
              <input
                id="tx-kind-income"
                type="radio"
                name="kind"
                value="income"
                checked={values.kind === "income"}
                onChange={() => set("kind", "income")}
              />
              Money in
            </label>
            <label className={f.choice}>
              <input
                type="radio"
                name="kind"
                value="expense"
                checked={values.kind === "expense"}
                onChange={() => set("kind", "expense")}
              />
              Money out
            </label>
          </div>
        </fieldset>

        {values.kind && (
          <div className={`${f.field} ${errors["tx-category"] ? f.hasError : ""}`}>
            <label className={f.label} htmlFor="tx-category">
              Category
            </label>
            <span id="tx-category-hint" className={f.hint}>
              HMRC’s own headings, so your figures go straight into your quarterly update.
            </span>
            {err("tx-category")}
            <select
              id="tx-category"
              className={f.control}
              value={values.category}
              onChange={(e) => set("category", e.target.value as TransactionCategory)}
              aria-invalid={errors["tx-category"] ? true : undefined}
              aria-describedby={describedBy(
                "tx-category-hint",
                errors["tx-category"] !== undefined && "tx-category-error",
                values.category !== "" &&
                  CATEGORY_HELP[values.category] !== undefined &&
                  "tx-category-help",
              )}
            >
              <option value="">Choose a category</option>
              {shown.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </select>
            {values.category && CATEGORY_HELP[values.category] && (
              <span id="tx-category-help" className={f.hint}>
                {CATEGORY_HELP[values.category]}
              </span>
            )}
          </div>
        )}

        <div className={`${f.field} ${errors["tx-date"] ? f.hasError : ""}`}>
          <label className={f.label} htmlFor="tx-date">
            Date
          </label>
          {err("tx-date")}
          <input
            id="tx-date"
            type="date"
            className={f.control}
            style={{ maxWidth: "14rem" }}
            value={values.date}
            max={today}
            onChange={(e) => set("date", e.target.value)}
            aria-invalid={errors["tx-date"] ? true : undefined}
            aria-describedby={describedBy(errors["tx-date"] !== undefined && "tx-date-error")}
          />
        </div>

        <div className={`${f.field} ${errors["tx-description"] ? f.hasError : ""}`}>
          <label className={f.label} htmlFor="tx-description">
            Description
          </label>
          {err("tx-description")}
          <input
            id="tx-description"
            className={f.control}
            value={values.description}
            maxLength={255}
            onChange={(e) => set("description", e.target.value)}
            aria-invalid={errors["tx-description"] ? true : undefined}
            aria-describedby={describedBy(
              errors["tx-description"] !== undefined && "tx-description-error",
            )}
            autoComplete="off"
          />
        </div>

        <div className={`${f.field} ${errors["tx-amount"] ? f.hasError : ""}`}>
          <label className={f.label} htmlFor="tx-amount">
            Amount
          </label>
          <span id="tx-amount-hint" className={f.hint}>
            {partShare
              ? `The full amount. Your ${trimPercentage(property.ownership_percentage)}% share is worked out for you.`
              : "The full amount, as it shows on your bank statement."}
          </span>
          {err("tx-amount")}
          <div className={f.money}>
            <span aria-hidden="true">£</span>
            <input
              id="tx-amount"
              inputMode="decimal"
              value={values.amount}
              onChange={(e) => set("amount", e.target.value)}
              aria-invalid={errors["tx-amount"] ? true : undefined}
              aria-describedby={describedBy(
                "tx-amount-hint",
                errors["tx-amount"] !== undefined && "tx-amount-error",
              )}
              autoComplete="off"
            />
          </div>
        </div>

        <div className={s.actions}>
          <Button type="submit" size="large" disabled={saving}>
            {saving ? "Saving…" : existing ? "Save changes" : "Add transaction"}
          </Button>
          <Link to={back}>Cancel</Link>
        </div>
      </form>
    </div>
  );
}
