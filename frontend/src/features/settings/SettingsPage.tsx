import { useState, type FormEvent } from "react";
import { Link } from "react-router";

import { useHmrcConnection, useMe, useSubmissions } from "../../api/queries";
import type { Landlord } from "../../api/types";
import { signOut } from "../../auth/session";
import { Button } from "../../components/Button";
import f from "../../components/Field.module.css";
import { Notice } from "../../components/Notice";
import { LoadFailed, Loading } from "../../components/QueryState";
import { usePageTitle } from "../../hooks/usePageTitle";
import { ukToday } from "../../lib/dates";
import { taxYearLabel, taxYearOf } from "../../lib/taxYear";
import { useUpdateMe } from "./mutations";
import s from "./Settings.module.css";

type Basis = Landlord["period_basis"];

/** /settings: your account, how your quarters run, HMRC, and about LedgerLet. */
export function SettingsPage() {
  usePageTitle("Settings");
  const me = useMe();

  return (
    <div className={s.page}>
      <h1 id="page-heading" tabIndex={-1}>
        Settings
      </h1>
      {me.isPending ? (
        <Loading label="your settings" />
      ) : me.isError ? (
        <LoadFailed what="your settings" error={me.error} retry={me.refetch} />
      ) : (
        <>
          <Account me={me.data} />
          <Quarters basis={me.data.period_basis} />
        </>
      )}
      <Hmrc />
      <About />
      <section className={s.section} aria-labelledby="signout-heading">
        <h2 id="signout-heading" className="visually-hidden">
          Sign out
        </h2>
        <div>
          <Button variant="secondary" onClick={signOut}>
            Sign out
          </Button>
        </div>
      </section>
    </div>
  );
}

function Account({ me }: { me: Landlord }) {
  const update = useUpdateMe();
  const [name, setName] = useState(me.display_name ?? "");
  const [error, setError] = useState<string>();
  const [saved, setSaved] = useState(false);

  function submit(e: FormEvent) {
    e.preventDefault();
    const value = name.trim();
    setSaved(false);
    if (!value) return setError("Enter a name, or leave it as it was");
    if (value.length > 100) return setError("Keep your name to 100 characters or fewer");
    setError(undefined);
    if (value === me.display_name) return;
    update.mutate(
      { display_name: value },
      { onSuccess: () => setSaved(true), onError: (err) => setError(err.message) },
    );
  }

  return (
    <section className={s.section} aria-labelledby="account-heading">
      <h2 id="account-heading">Your account</h2>
      <dl className={s.facts}>
        <dt>Signed in as</dt>
        <dd>{me.email ?? "A development sign-in, with no email address"}</dd>
      </dl>
      {saved && <Notice>Name saved.</Notice>}
      <form className={s.inlineForm} onSubmit={submit} noValidate>
        <div className={`${f.field} ${error ? f.hasError : ""}`}>
          <label className={f.label} htmlFor="me-name">
            Your name
          </label>
          <span id="me-name-hint" className={f.hint}>
            How LedgerLet refers to you.
          </span>
          {error && (
            <span id="me-name-error" className={f.error}>
              <span className="visually-hidden">Error: </span>
              {error}
            </span>
          )}
          <input
            id="me-name"
            className={`${f.control} ${s.nameInput}`}
            value={name}
            onChange={(e) => setName(e.target.value)}
            autoComplete="name"
            aria-invalid={error ? true : undefined}
            aria-describedby={`me-name-hint${error ? " me-name-error" : ""}`}
          />
        </div>
        <div>
          <Button type="submit" variant="secondary" disabled={update.isPending}>
            {update.isPending ? "Saving…" : "Save name"}
          </Button>
        </div>
      </form>
    </section>
  );
}

const BASES: { value: Basis; label: string; text: string }[] = [
  {
    value: "standard",
    label: "Standard: to the 5th",
    text: "Quarters run from 6 April and end on 5 July, 5 October, 5 January and 5 April. Most landlords use these.",
  },
  {
    value: "calendar",
    label: "Calendar: to the end of the month",
    text: "Quarters run from 1 April and end on 30 June, 30 September, 31 December and 31 March. Useful if your records follow calendar months.",
  },
];

/** Standard or calendar quarters. Fixed for the year once HMRC has an update. */
function Quarters({ basis }: { basis: Basis }) {
  const year = taxYearOf(ukToday());
  const submissions = useSubmissions(year);
  const update = useUpdateMe();
  const [choice, setChoice] = useState<Basis>(basis);
  const [saved, setSaved] = useState(false);
  const sent = submissions.data?.some((x) => x.succeeded) ?? false;

  return (
    <section className={s.section} aria-labelledby="quarters-heading">
      <h2 id="quarters-heading">Your quarters</h2>
      {saved && <Notice>Quarters changed. Every date in LedgerLet now follows them.</Notice>}
      {sent ? (
        <>
          <p className={s.current}>
            {BASES.find((b) => b.value === basis)?.label}
            <span className={s.meta}>{BASES.find((b) => b.value === basis)?.text}</span>
          </p>
          <p className={s.note}>
            You’ve already sent HMRC an update for {taxYearLabel(year)}, so this can’t change until
            the next tax year. Every update in a year must use the same quarters.
          </p>
        </>
      ) : (
        <form
          className={s.inlineForm}
          onSubmit={(e) => {
            e.preventDefault();
            setSaved(false);
            if (choice !== basis)
              update.mutate({ period_basis: choice }, { onSuccess: () => setSaved(true) });
          }}
        >
          <fieldset className={s.choices}>
            <legend className={f.label}>When do your quarters end?</legend>
            {BASES.map((b) => (
              <div key={b.value} className={s.option}>
                <input
                  id={`basis-${b.value}`}
                  type="radio"
                  name="basis"
                  checked={choice === b.value}
                  onChange={() => setChoice(b.value)}
                  aria-describedby={`basis-${b.value}-text`}
                />
                <div className={s.optionBody}>
                  <label htmlFor={`basis-${b.value}`} className={s.optionLabel}>
                    {b.label}
                  </label>
                  <span id={`basis-${b.value}-text`} className={s.optionText}>
                    {b.text}
                  </span>
                </div>
              </div>
            ))}
          </fieldset>
          <p className={s.note}>
            HMRC lets you choose. Once you’ve sent an update this tax year, the choice is fixed
            until the next one.
          </p>
          {update.isError && (
            <p role="alert" className={s.problem}>
              {update.error.message}
            </p>
          )}
          <div>
            <Button
              type="submit"
              variant="secondary"
              disabled={update.isPending || choice === basis}
            >
              {update.isPending ? "Saving…" : "Save quarters"}
            </Button>
          </div>
        </form>
      )}
    </section>
  );
}

function Hmrc() {
  const connection = useHmrcConnection();
  return (
    <section className={s.section} aria-labelledby="hmrc-heading">
      <h2 id="hmrc-heading">HMRC</h2>
      <p>
        {connection.isPending
          ? "Checking your connection…"
          : connection.isError
            ? "Couldn’t check your connection right now."
            : connection.data.connected
              ? "Connected. LedgerLet can send your quarterly updates."
              : "Not connected yet. LedgerLet needs your permission to send updates."}
      </p>
      <Link className={s.strong} to="/settings/hmrc">
        {connection.data?.connected === false ? "Connect to HMRC" : "Manage HMRC connection"}
      </Link>
    </section>
  );
}

function About() {
  return (
    <section className={s.section} aria-labelledby="about-heading">
      <h2 id="about-heading">About LedgerLet</h2>
      <p className={s.prose}>
        LedgerLet keeps the income and expenses of the properties you let, works out your share, and
        sends your quarterly updates to HMRC for Making Tax Digital for Income Tax.
      </p>
      <p className={s.note}>
        LedgerLet is independent software. It isn’t made or endorsed by HMRC.
      </p>
      <p>
        <Link className={s.strong} to="/privacy">
          Privacy notice
        </Link>
        {" · "}
        <Link className={s.strong} to="/terms">
          Terms of use
        </Link>
      </p>
      <p className={s.credit}>
        © 2026 LedgerLet. Built in London by{" "}
        <a href="https://shazmoghaddam.github.io/" rel="author">
          Shaz Moghaddam
        </a>
        .
      </p>
    </section>
  );
}
