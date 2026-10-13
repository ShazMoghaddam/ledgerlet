import { useState, type FormEvent } from "react";
import { Navigate, useNavigate, useSearchParams } from "react-router";

import { signIn, signInMethod, startSignIn } from "../../auth/session";
import { safeNext, useSignedIn } from "../../auth/useSession";
import { Button } from "../../components/Button";
import { Mark } from "../../components/Mark";
import { LegalFooter } from "../legal/LegalPage";
import { usePageTitle } from "../../hooks/usePageTitle";
import s from "./SignInPage.module.css";

/**
 * Sign in. With Auth0, a button that goes to Auth0's own sign-in page (where new
 * landlords can also create an account). In local development, a box for a token
 * from scripts/dev_auth.py. A build with neither says so rather than pretending.
 */
export function SignInPage() {
  usePageTitle("Sign in");
  const signedIn = useSignedIn();
  const [params] = useSearchParams();
  const next = safeNext(params.get("next"));
  if (signedIn) return <Navigate to={next} replace />;

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
        {signInMethod === "auth0" ? (
          <Auth0SignIn next={next} />
        ) : signInMethod === "dev-token" ? (
          <DevTokenForm next={next} />
        ) : (
          <p>Sign-in isn’t available yet.</p>
        )}
      </div>
      <LegalFooter />
    </main>
  );
}

function Auth0SignIn({ next }: { next: string }) {
  const [going, setGoing] = useState(false);
  const [failed, setFailed] = useState(false);
  return (
    <div style={{ display: "grid", gap: "var(--space-4)" }}>
      <p>Sign in, or create an account if you’re new. It only takes your email address.</p>
      {failed && (
        <p role="alert" className={s.error}>
          Couldn’t reach the sign-in page. Check your connection and try again.
        </p>
      )}
      <Button
        size="large"
        disabled={going}
        onClick={() => {
          setGoing(true);
          setFailed(false);
          startSignIn(next).catch(() => {
            setGoing(false);
            setFailed(true);
          });
        }}
      >
        {going ? "Going to sign-in…" : "Continue to sign in"}
      </Button>
    </div>
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
    navigate(next, { replace: true, state: { signedIn: true } });
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
