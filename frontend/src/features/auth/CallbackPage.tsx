import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router";

import { finishSignIn } from "../../auth/session";
import { safeNext } from "../../auth/useSession";
import { Mark } from "../../components/Mark";
import { usePageTitle } from "../../hooks/usePageTitle";
import s from "./SignInPage.module.css";

/** /sign-in/callback: Auth0 sends the browser back here after signing in. */
export function CallbackPage() {
  usePageTitle("Signing in");
  const navigate = useNavigate();
  const [failed, setFailed] = useState<string>();

  useEffect(() => {
    finishSignIn()
      .then((next) => navigate(safeNext(next), { replace: true, state: { signedIn: true } }))
      .catch((err: unknown) => setFailed(callbackError(err)));
  }, [navigate]);

  return (
    <main className={s.page}>
      <div className={s.card}>
        <span className={s.brand}>
          <Mark />
          LedgerLet
        </span>
        <h1 id="page-heading" tabIndex={-1}>
          {failed ? "Sign-in didn’t finish" : "Signing you in…"}
        </h1>
        {failed && (
          <p role="alert">
            {failed} <Link to="/sign-in">Try signing in again</Link>.
          </p>
        )}
      </div>
    </main>
  );
}

/**
 * Why sign-in didn't finish, in words the landlord can act on. Auth0 reports its
 * reason as `error` and `error_description` (on the thrown error, from the address).
 */
export function callbackError(err: unknown): string {
  const { error, error_description: description } = (err ?? {}) as {
    error?: unknown;
    error_description?: unknown;
  };
  if (error === "access_denied" && !description) return "You chose not to give LedgerLet access.";
  if (typeof description === "string" && description.trim())
    return `The sign-in service said: “${description.trim().replace(/[.\s]+$/, "")}.”`;
  return "The sign-in link may have expired or already been used.";
}
