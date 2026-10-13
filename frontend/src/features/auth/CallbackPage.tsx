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
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    finishSignIn()
      .then((next) => navigate(safeNext(next), { replace: true, state: { signedIn: true } }))
      .catch(() => setFailed(true));
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
            The sign-in link may have expired or already been used.{" "}
            <Link to="/sign-in">Try signing in again</Link>.
          </p>
        )}
      </div>
    </main>
  );
}
