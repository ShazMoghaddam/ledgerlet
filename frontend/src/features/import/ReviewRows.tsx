import { useMemo, useState, type FormEvent } from "react";

import { ApiError } from "../../api/client";
import { useCategories } from "../../api/queries";
import type {
  Category,
  ImportPreview,
  ImportResult,
  ImportRowConfirm,
  PreviewRow,
  Property,
  TransactionCategory,
} from "../../api/types";
import { Amount } from "../../components/Amount";
import { Button } from "../../components/Button";
import { ErrorSummary, type FieldError } from "../../components/ErrorSummary";
import f from "../../components/Field.module.css";
import { LoadFailed, Loading } from "../../components/QueryState";
import { formatLong, formatShort } from "../../lib/dates";
import { formatPounds } from "../../lib/money";
import { useConfirmImport } from "./mutations";
import s from "./Import.module.css";

interface Choice {
  include: boolean;
  category: TransactionCategory | "";
}

/** A row that can be imported: it was read, and hasn't been imported before. */
const importable = (r: PreviewRow) => r.status === "new" || r.status === "possible_duplicate";
const kindOf = (r: PreviewRow) => r.suggested_kind;

/**
 * Every row in the file, so nothing disappears silently. New rows start ticked,
 * possible duplicates unticked; categories start from what the landlord used last
 * time. Nothing is saved until "Import".
 */
export function ReviewRows({
  preview,
  property,
  onBack,
  onImported,
}: {
  preview: ImportPreview;
  property: Property;
  onBack: () => void;
  onImported: (result: ImportResult) => void;
}) {
  const categories = useCategories();
  const confirm = useConfirmImport();
  const rows = useMemo(() => [...preview.rows].sort((a, b) => a.line - b.line), [preview.rows]);
  const [choices, setChoices] = useState<Record<number, Choice>>(() =>
    Object.fromEntries(
      rows.map((r) => [
        r.line,
        { include: r.status === "new", category: r.suggested_category ?? "" },
      ]),
    ),
  );
  const [missing, setMissing] = useState<Set<number>>(new Set());
  const [summary, setSummary] = useState<FieldError[]>([]);

  if (categories.isPending) return <Loading label="the categories" />;
  if (categories.isError)
    return <LoadFailed what="the categories" error={categories.error} retry={categories.refetch} />;

  const choose = (line: number, change: Partial<Choice>) =>
    setChoices((c) => ({ ...c, [line]: { ...c[line]!, ...change } }));
  const selected = rows.filter((r) => importable(r) && choices[r.line]?.include);

  function submit(e: FormEvent) {
    e.preventDefault();
    const gaps = selected.filter((r) => !choices[r.line]?.category).map((r) => r.line);
    setMissing(new Set(gaps));
    if (gaps.length) {
      setSummary([
        {
          field: `row-${gaps[0]}`,
          message:
            gaps.length === 1
              ? "Choose a category for 1 row you’re importing"
              : `Choose a category for ${gaps.length} rows you’re importing`,
        },
      ]);
      return;
    }
    setSummary([]);
    const payload: ImportRowConfirm[] = selected.map((r) => ({
      fingerprint: r.fingerprint!,
      transaction_date: r.transaction_date!,
      description: r.description,
      amount: r.amount!,
      direction: r.direction!,
      category: choices[r.line]!.category as TransactionCategory,
    }));
    confirm.mutate(
      { propertyId: property.id, rows: payload },
      {
        onSuccess: onImported,
        onError: (error) =>
          setSummary([
            {
              message:
                error instanceof ApiError
                  ? `Nothing was imported: ${error.message}`
                  : "Nothing was imported. Check your connection and try again.",
            },
          ]),
      },
    );
  }

  const counts = [
    [preview.new, "new"],
    [
      preview.possible_duplicates,
      preview.possible_duplicates === 1 ? "possible duplicate" : "possible duplicates",
    ],
    [preview.already_imported, "imported before"],
    [preview.invalid, preview.invalid === 1 ? "couldn’t be read" : "couldn’t be read"],
  ] as const;

  return (
    <form className={s.page} onSubmit={submit} noValidate>
      <p className={s.intro}>
        {preview.total} {preview.total === 1 ? "row" : "rows"} for {property.nickname}. Tick the
        ones to import and give each a category.
      </p>
      <ul className={s.counts} aria-label="What’s in the file">
        {counts
          .filter(([n]) => n > 0)
          .map(([n, label]) => (
            <li key={label}>
              <strong className="num">{n}</strong> {label}
            </li>
          ))}
      </ul>

      {preview.new === 0 && (
        <p className={s.intro} role="status">
          {preview.possible_duplicates > 0
            ? "Nothing new in this file. The possible duplicates are unticked: tick any that are different payments."
            : "Nothing new to import: everything in this file that could be read is already in LedgerLet."}
        </p>
      )}

      <ErrorSummary errors={summary} />

      <BulkCategory
        rows={selected}
        choices={choices}
        categories={categories.data}
        onApply={choose}
      />

      <ul className={s.rows}>
        {rows.map((r) => (
          <Row
            key={r.line}
            row={r}
            choice={choices[r.line]!}
            categories={categories.data}
            missing={missing.has(r.line)}
            onChange={(change) => {
              choose(r.line, change);
              if (change.category) setMissing((m) => new Set([...m].filter((x) => x !== r.line)));
            }}
          />
        ))}
      </ul>

      <div className={s.sticky}>
        <span className="num" aria-live="polite">
          {selected.length} of {rows.filter(importable).length} rows selected
        </span>
        <div className={s.actions}>
          <Button variant="quiet" onClick={onBack}>
            Start again
          </Button>
          <Button type="submit" size="large" disabled={selected.length === 0 || confirm.isPending}>
            {confirm.isPending
              ? "Importing…"
              : `Import ${selected.length} ${selected.length === 1 ? "transaction" : "transactions"}`}
          </Button>
        </div>
      </div>
    </form>
  );
}

function Row({
  row: r,
  choice,
  categories,
  missing,
  onChange,
}: {
  row: PreviewRow;
  choice: Choice;
  categories: Category[];
  missing: boolean;
  onChange: (change: Partial<Choice>) => void;
}) {
  const can = importable(r);
  const direction = r.direction === "in" ? "in" : "out";
  const what = `${r.description}, ${r.transaction_date ? formatLong(r.transaction_date) : `line ${r.line}`}${
    r.amount ? `, ${formatPounds(r.amount)} ${direction}` : ""
  }`;
  const options = categories.filter((c) => c.kind === kindOf(r));
  const id = `row-${r.line}`;

  return (
    <li className={`${s.row} ${can ? "" : s.skipped}`}>
      <input
        type="checkbox"
        checked={can && choice.include}
        disabled={!can}
        onChange={(e) => onChange({ include: e.target.checked })}
        aria-label={`Import ${what}`}
      />
      <div className={s.rowMain}>
        <span>
          {r.description}
          <span className={s.meta}>
            {r.transaction_date ? formatShort(r.transaction_date) : "No date"}, line {r.line}
          </span>
        </span>
        {r.amount && (
          <Amount
            className={s.amount}
            pounds={r.direction === "in" ? r.amount : `-${r.amount}`}
            signed
            symbol={false}
          />
        )}
      </div>

      {can && (
        <div className={`${s.rowCategory} ${f.field} ${missing ? f.hasError : ""}`}>
          <label htmlFor={id} className="visually-hidden">
            Category for {what}
          </label>
          {missing && (
            <span id={`${id}-error`} className={f.error}>
              Choose a category
            </span>
          )}
          <select
            id={id}
            className={f.control}
            value={choice.category}
            onChange={(e) =>
              onChange({ category: e.target.value as TransactionCategory, include: true })
            }
            aria-invalid={missing ? true : undefined}
            aria-describedby={missing ? `${id}-error` : undefined}
          >
            <option value="">
              {direction === "in" ? "Money in: choose…" : "Money out: choose…"}
            </option>
            {options.map((c) => (
              <option key={c.value} value={c.value}>
                {c.label}
              </option>
            ))}
          </select>
          {r.suggested_category && choice.category === r.suggested_category && (
            <span className={s.suggested}>Same as last time</span>
          )}
        </div>
      )}

      {r.status === "possible_duplicate" && (
        <p className={`${s.flag} ${s.flagWarn}`}>
          Same date and amount as one you’ve already recorded. Tick it only if it’s a different
          payment.
        </p>
      )}
      {r.status === "already_imported" && (
        <p className={s.flag}>Imported before, so it’s skipped.</p>
      )}
      {r.status === "invalid" && (
        <p className={`${s.flag} ${s.flagBad}`}>
          Couldn’t be read: {r.message?.replace(/\.$/, "")}. Correct it in the file and import
          again, or add it by hand.
        </p>
      )}
    </li>
  );
}

/** Give every selected row of one direction that has no category yet the same one. */
function BulkCategory({
  rows,
  choices,
  categories,
  onApply,
}: {
  rows: PreviewRow[];
  choices: Record<number, Choice>;
  categories: Category[];
  onApply: (line: number, change: Partial<Choice>) => void;
}) {
  const [value, setValue] = useState<TransactionCategory | "">("");
  const blank = rows.filter((r) => !choices[r.line]?.category);
  const outs = blank.filter((r) => r.direction === "out");
  const ins = blank.filter((r) => r.direction === "in");
  if (blank.length < 2) return null;

  const apply = () => {
    const kind = categories.find((c) => c.value === value)?.kind;
    for (const r of kind === "income" ? ins : outs)
      onApply(r.line, { category: value as TransactionCategory });
    setValue("");
  };

  return (
    <div className={s.bulk}>
      <div className={f.field}>
        <label className={f.label} htmlFor="bulk-category">
          Fill in rows without a category
        </label>
        <span className={f.hint}>
          A money out category goes on every selected money out row that hasn’t got one yet; a money
          in category on the money in rows.
        </span>
        <select
          id="bulk-category"
          className={f.control}
          value={value}
          onChange={(e) => setValue(e.target.value as TransactionCategory)}
        >
          <option value="">Choose a category</option>
          {outs.length > 0 && (
            <optgroup label={`Money out (${outs.length})`}>
              {categories
                .filter((c) => c.kind === "expense")
                .map((c) => (
                  <option key={c.value} value={c.value}>
                    {c.label}
                  </option>
                ))}
            </optgroup>
          )}
          {ins.length > 0 && (
            <optgroup label={`Money in (${ins.length})`}>
              {categories
                .filter((c) => c.kind === "income")
                .map((c) => (
                  <option key={c.value} value={c.value}>
                    {c.label}
                  </option>
                ))}
            </optgroup>
          )}
        </select>
      </div>
      <Button variant="secondary" onClick={apply} disabled={!value}>
        Apply
      </Button>
    </div>
  );
}
