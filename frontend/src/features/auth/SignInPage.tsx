import { useState, type FormEvent } from "react";
import { Navigate, useNavigate, useSearchParams } from "react-router";

import { signIn } from "../../auth/session";
import { safeNext, useToken } from "../../auth/useSession";
import { Button } from "../../components/Button";
import { Mark } from "../../components/Mark";
import { usePageTitle } from "../../hooks/usePageTitle";
import s from "./SignInPage.module.css";

/**
 * Development sign-in: paste a token from scripts/dev_auth.py.
 *
 * Production will send the landlord to the chosen identity provider instead. Until
 * that's chosen, a production build says so rather than offering a token box.
 */
export function SignInPage() {
  usePageTitle("Sign in");
  const token = useToken();
  const [params] = useSearchParams();
  const next = safeNext(params.get("next"));
  if (token) return <Navigate to={next} replace />;

  return (
    <main className={s.page}>
      <div className={s.card}>
        <span className={s.brand}>
          <Mark />
          LedgerLet
        </span>
        <h1 id="page-heading" tabIndex={-1}>
          Sign in
        </h1>
        {import.meta.env.DEV ? <DevTokenForm next={next} /> : <p>Sign-in isn’t available yet.</p>}
      </div>
    </main>
  );
}

function DevTokenForm({ next }: { next: string }) {
  const navigate = useNavigate();
  const [value, setValue] = useState("");
  const [error, setError] = useState<string | null>(null);

  function submit(event: FormEvent) {
    event.preventDefault();
    // A JWT is three base64url parts. This only catches a bad paste; the API checks it properly.
    if (!/^[\w-]+\.[\w-]+\.[\w-]+$/.test(value.trim())) {
      setError("Paste the whole token: three parts separated by dots");
      return;
    }
    signIn(value);
    navigate(next, { replace: true });
  }

  return (
    <form onSubmit={submit} noValidate style={{ display: "grid", gap: "var(--space-5)" }}>
      <div className={s.field}>
        <label htmlFor="token">Development token</label>
        <span id="token-hint" className={s.hint}>
          Make one in your terminal with <code>python scripts/dev_auth.py token --sub shaz</code>
        </span>
        {error && (
          <span id="token-error" className={s.error}>
            {error}
          </span>
        )}
        <textarea
          id="token"
          name="token"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          aria-describedby={error ? "token-hint token-error" : "token-hint"}
          aria-invalid={error ? true : undefined}
          autoComplete="off"
          spellCheck={false}
        />
      </div>
      <Button type="submit" size="large">
        Sign in
      </Button>
    </form>
  );
}
