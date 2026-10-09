import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { Link, useSearchParams } from "react-router";

import { ApiError } from "../../api/client";
import { useProperties } from "../../api/queries";
import type { ImportPreview, ImportResult, Property } from "../../api/types";
import { Button, ButtonLink } from "../../components/Button";
import { ErrorSummary, type FieldError } from "../../components/ErrorSummary";
import f from "../../components/Field.module.css";
import { Notice } from "../../components/Notice";
import { LoadFailed, Loading } from "../../components/QueryState";
import { usePageTitle } from "../../hooks/usePageTitle";
import { glimpse, readStart, type CsvGlimpse } from "../../lib/csv";
import { DATE_FORMATS, guessMapping, type Mapping } from "../../lib/importMapping";
import { usePreviewImport } from "./mutations";
import { ReviewRows } from "./ReviewRows";
import s from "./Import.module.css";

const MAX_BYTES = 2 * 1024 * 1024;

type Step =
  | { name: "choose" }
  | { name: "match"; propertyId: string; file: File; csv: CsvGlimpse }
  | { name: "review"; propertyId: string; preview: ImportPreview }
  | { name: "done"; propertyId: string; result: ImportResult };

const STEP_LABELS = ["Choose the statement", "Match the columns", "Check and import"];

/**
 * Importing a bank statement, in three steps. Nothing is saved until the last one.
 * The steps live in this page rather than the URL: the file can't survive a reload,
 * so a reload honestly starts again.
 */
export function ImportPage() {
  usePageTitle("Import a bank statement");
  const properties = useProperties();
  const [step, setStep] = useState<Step>({ name: "choose" });
  const heading = useRef<HTMLHeadingElement>(null);

  // Each new step is announced by moving focus to its heading.
  const first = useRef(true);
  useEffect(() => {
    if (first.current) {
      first.current = false;
      return;
    }
    heading.current?.focus();
  }, [step.name]);

  if (properties.isPending) return <Loading label="your properties" />;
  if (properties.isError)
    return (
      <LoadFailed what="your properties" error={properties.error} retry={properties.refetch} />
    );
  const active = properties.data.filter((p) => !p.is_archived);
  const property = (id: string) => active.find((p) => p.id === id);
  const index = { choose: 0, match: 1, review: 2, done: 3 }[step.name];

  return (
    <div className={s.page}>
      <Link to="/transactions" className={s.back}>
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
      <h1 id="page-heading" ref={heading} tabIndex={-1}>
        {step.name === "done" ? "Statement imported" : "Import a bank statement"}
      </h1>
      {step.name !== "done" && (
        <ol className={s.steps} aria-label="Steps">
          {STEP_LABELS.map((label, i) => (
            <li
              key={label}
              className={i < index ? s.done : undefined}
              aria-current={i === index ? "step" : undefined}
            >
              {label}
            </li>
          ))}
        </ol>
      )}

      {active.length === 0 ? (
        <p>
          Statements are imported into a property. <Link to="/properties/new">Add a property</Link>{" "}
          first.
        </p>
      ) : step.name === "choose" ? (
        <ChooseFile
          properties={active}
          onChosen={(propertyId, file, csv) => setStep({ name: "match", propertyId, file, csv })}
        />
      ) : step.name === "match" ? (
        <MatchColumns
          step={step}
          propertyName={property(step.propertyId)?.nickname ?? ""}
          onBack={() => setStep({ name: "choose" })}
          onPreview={(preview) => setStep({ name: "review", propertyId: step.propertyId, preview })}
        />
      ) : step.name === "review" ? (
        <ReviewRows
          preview={step.preview}
          property={property(step.propertyId)!}
          onBack={() => setStep({ name: "choose" })}
          onImported={(result) => setStep({ name: "done", propertyId: step.propertyId, result })}
        />
      ) : (
        <Done
          result={step.result}
          property={property(step.propertyId)}
          onAnother={() => setStep({ name: "choose" })}
        />
      )}
    </div>
  );
}

function ChooseFile({
  properties,
  onChosen,
}: {
  properties: Property[];
  onChosen: (propertyId: string, file: File, csv: CsvGlimpse) => void;
}) {
  const [params] = useSearchParams();
  const wanted = params.get("property");
  const [propertyId, setPropertyId] = useState(
    properties.find((p) => p.id === wanted)?.id ??
      (properties.length === 1 ? properties[0]!.id : ""),
  );
  const [file, setFile] = useState<File | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [summary, setSummary] = useState<FieldError[]>([]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    const found: Record<string, string> = {};
    if (!propertyId) found["import-property"] = "Choose the property the statement is for";
    if (!file) found["import-file"] = "Choose a CSV file exported from your bank";
    else if (!/\.csv$/i.test(file.name) && file.type !== "text/csv")
      found["import-file"] = "The file must be a CSV. Most banks offer this as an export option";
    else if (file.size > MAX_BYTES)
      found["import-file"] = "The file is larger than 2 MB. Export fewer months at a time";

    let csv: CsvGlimpse | null = null;
    if (file && !found["import-file"]) {
      csv = glimpse(await readStart(file));
      if (csv.columns.length < 2)
        found["import-file"] = "This doesn’t look like a statement: no column headings found";
    }
    setErrors(found);
    setSummary(Object.entries(found).map(([field, message]) => ({ field, message })));
    if (!Object.keys(found).length && file && csv) onChosen(propertyId, file, csv);
  }

  return (
    <>
      <p className={s.intro}>
        Export a CSV from your bank for the account the rent goes into. You’ll see every row before
        anything is saved, and rows you’ve imported before are skipped.
      </p>
      <ErrorSummary errors={summary} />
      <form className={s.form} onSubmit={submit} noValidate>
        <div className={`${f.field} ${errors["import-property"] ? f.hasError : ""}`}>
          <label className={f.label} htmlFor="import-property">
            Property
          </label>
          {errors["import-property"] && (
            <span id="import-property-error" className={f.error}>
              {errors["import-property"]}
            </span>
          )}
          <select
            id="import-property"
            className={f.control}
            value={propertyId}
            onChange={(e) => setPropertyId(e.target.value)}
            aria-invalid={errors["import-property"] ? true : undefined}
            aria-describedby={errors["import-property"] ? "import-property-error" : undefined}
          >
            <option value="">Choose a property</option>
            {properties.map((p) => (
              <option key={p.id} value={p.id}>
                {p.nickname}
              </option>
            ))}
          </select>
        </div>
        <div className={`${f.field} ${errors["import-file"] ? f.hasError : ""}`}>
          <label className={f.label} htmlFor="import-file">
            Statement file
          </label>
          <span id="import-file-hint" className={f.hint}>
            A CSV file, up to 2 MB
          </span>
          {errors["import-file"] && (
            <span id="import-file-error" className={f.error}>
              {errors["import-file"]}
            </span>
          )}
          <input
            id="import-file"
            type="file"
            accept=".csv,text/csv"
            className={s.file}
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            aria-invalid={errors["import-file"] ? true : undefined}
            aria-describedby={
              errors["import-file"] ? "import-file-hint import-file-error" : "import-file-hint"
            }
          />
        </div>
        <div className={s.actions}>
          <Button type="submit" size="large">
            Continue
          </Button>
        </div>
      </form>
    </>
  );
}

function MatchColumns({
  step,
  propertyName,
  onBack,
  onPreview,
}: {
  step: Extract<Step, { name: "match" }>;
  propertyName: string;
  onBack: () => void;
  onPreview: (preview: ImportPreview) => void;
}) {
  const { columns, examples } = step.csv;
  const [mapping, setMapping] = useState<Mapping>(() => guessMapping(columns, examples));
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [summary, setSummary] = useState<FieldError[]>([]);
  const preview = usePreviewImport();
  const set = <K extends keyof Mapping>(key: K, value: Mapping[K]) =>
    setMapping((m) => ({ ...m, [key]: value }));

  function submit(e: FormEvent) {
    e.preventDefault();
    const found: Record<string, string> = {};
    if (!mapping.dateColumn) found["map-date"] = "Choose the column with the date";
    if (!mapping.descriptionColumn)
      found["map-description"] = "Choose the column that describes each payment";
    if (mapping.amountStyle === "signed" && !mapping.amountColumn)
      found["map-amount"] = "Choose the amount column";
    if (mapping.amountStyle === "split") {
      if (!mapping.paidInColumn) found["map-in"] = "Choose the column for money in";
      if (!mapping.paidOutColumn) found["map-out"] = "Choose the column for money out";
    }
    setErrors(found);
    setSummary(Object.entries(found).map(([field, message]) => ({ field, message })));
    if (Object.keys(found).length) return;
    preview.mutate(
      { propertyId: step.propertyId, file: step.file, mapping },
      {
        onSuccess: onPreview,
        onError: (error) =>
          setSummary([
            {
              message:
                error instanceof ApiError
                  ? `The statement couldn’t be read with these settings: ${error.message}`
                  : "Couldn’t send the file. Check your connection and try again.",
            },
          ]),
      },
    );
  }

  const column = (
    id: string,
    label: string,
    key: "dateColumn" | "descriptionColumn" | "amountColumn" | "paidInColumn" | "paidOutColumn",
    hint?: string,
  ) => (
    <div className={`${f.field} ${errors[id] ? f.hasError : ""}`}>
      <label className={f.label} htmlFor={id}>
        {label}
      </label>
      {hint && (
        <span id={`${id}-hint`} className={f.hint}>
          {hint}
        </span>
      )}
      {errors[id] && (
        <span id={`${id}-error`} className={f.error}>
          {errors[id]}
        </span>
      )}
      <select
        id={id}
        className={f.control}
        value={mapping[key]}
        onChange={(e) => set(key, e.target.value)}
        aria-invalid={errors[id] ? true : undefined}
        aria-describedby={
          [hint && `${id}-hint`, errors[id] && `${id}-error`].filter(Boolean).join(" ") || undefined
        }
      >
        <option value="">Choose a column</option>
        {columns.map((c) => (
          <option key={c} value={c}>
            {c}
          </option>
        ))}
      </select>
    </div>
  );

  return (
    <>
      <p className={s.intro}>
        <strong>{step.file.name}</strong> for {propertyName}. Here are its first rows; say which
        column is which. We’ve made a first guess.
      </p>
      {/* Focusable so keyboard users can scroll a wide file sideways (axe: scrollable-region-focusable). */}
      {/* eslint-disable-next-line jsx-a11y/no-noninteractive-tabindex */}
      <div className={s.sampleWrap} tabIndex={0} role="region" aria-label="The start of your file">
        <table className={`${s.sample} num`}>
          <thead>
            <tr>
              {columns.map((c) => (
                <th key={c} scope="col">
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {examples.map((row, i) => (
              <tr key={i}>
                {columns.map((c, j) => (
                  <td key={c}>{row[j] ?? ""}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <ErrorSummary errors={summary} />
      <form className={s.form} onSubmit={submit} noValidate>
        <div className={s.pair}>
          {column("map-date", "Date", "dateColumn")}
          <div className={f.field}>
            <label className={f.label} htmlFor="map-date-format">
              Dates look like
            </label>
            <select
              id="map-date-format"
              className={f.control}
              value={mapping.dateFormat}
              onChange={(e) => set("dateFormat", e.target.value)}
            >
              {DATE_FORMATS.map((d) => (
                <option key={d.value} value={d.value}>
                  {d.label}
                </option>
              ))}
            </select>
          </div>
        </div>
        {column("map-description", "Description", "descriptionColumn", "The payee or reference")}

        <fieldset className={f.choices}>
          <legend>How does the statement show amounts?</legend>
          <div className={f.options}>
            <label className={f.choice}>
              <input
                type="radio"
                name="amount-style"
                checked={mapping.amountStyle === "signed"}
                onChange={() => set("amountStyle", "signed")}
              />
              One amount column
            </label>
            <label className={f.choice}>
              <input
                type="radio"
                name="amount-style"
                checked={mapping.amountStyle === "split"}
                onChange={() => set("amountStyle", "split")}
              />
              Separate money in and out columns
            </label>
          </div>
        </fieldset>

        {mapping.amountStyle === "signed" ? (
          <>
            {column(
              "map-amount",
              "Amount",
              "amountColumn",
              "Usually money out is shown with a minus sign",
            )}
            <label className={s.check}>
              <input
                type="checkbox"
                checked={mapping.invertSign}
                onChange={(e) => set("invertSign", e.target.checked)}
              />
              <span>
                My bank shows money out as a positive number
                <span className={f.hint} style={{ display: "block" }}>
                  Tick this if payments you made appear without a minus sign
                </span>
              </span>
            </label>
          </>
        ) : (
          <div className={s.pair}>
            {column("map-in", "Money in", "paidInColumn")}
            {column("map-out", "Money out", "paidOutColumn")}
          </div>
        )}

        <div className={s.actions}>
          <Button type="submit" size="large" disabled={preview.isPending}>
            {preview.isPending ? "Reading the statement…" : "Continue"}
          </Button>
          <Button variant="quiet" onClick={onBack}>
            Choose a different file
          </Button>
        </div>
      </form>
    </>
  );
}

function Done({
  result,
  property,
  onAnother,
}: {
  result: ImportResult;
  property?: Property;
  onAnother: () => void;
}) {
  const n = result.created;
  const lines: ReactNode[] = [];
  if (result.skipped_already_imported > 0)
    lines.push(
      `${result.skipped_already_imported} ${result.skipped_already_imported === 1 ? "row was" : "rows were"} imported before, so ${result.skipped_already_imported === 1 ? "it was" : "they were"} skipped.`,
    );
  return (
    <div className={`${s.form} ${s.narrow}`}>
      <Notice>{`${n} ${n === 1 ? "transaction" : "transactions"} added to ${property?.nickname ?? "the property"}.`}</Notice>
      {lines.map((l, i) => (
        <p key={i}>{l}</p>
      ))}
      <p className={s.intro}>They’re in your figures for the quarter straight away.</p>
      <div className={s.actions}>
        <ButtonLink to={`/transactions${property ? `?property=${property.id}` : ""}`}>
          See {property?.nickname ?? "the"} transactions
        </ButtonLink>
        <Button variant="quiet" onClick={onAnother}>
          Import another statement
        </Button>
      </div>
    </div>
  );
}
