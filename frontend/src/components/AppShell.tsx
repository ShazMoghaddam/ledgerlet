import { useEffect, useRef, type ComponentType } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router";

import { useHmrcConnection, useMe, useObligations } from "../api/queries";
import { signOut } from "../auth/session";
import {
  CheckIcon,
  OverviewIcon,
  PropertiesIcon,
  SettingsIcon,
  TaxIcon,
  TransactionsIcon,
} from "./Icons";
import { Mark } from "./Mark";
import s from "./AppShell.module.css";

const SECTIONS: { to: string; label: string; Icon: ComponentType<{ size?: number }> }[] = [
  { to: "/", label: "Overview", Icon: OverviewIcon },
  { to: "/transactions", label: "Transactions", Icon: TransactionsIcon },
  { to: "/tax", label: "Tax", Icon: TaxIcon },
  { to: "/properties", label: "Properties", Icon: PropertiesIcon },
  { to: "/settings", label: "Settings", Icon: SettingsIcon },
];

export function AppShell() {
  useFocusHeadingOnNavigate();
  const obligations = useObligations();
  const yearLabel = obligations.data ? `Tax year ${obligations.data.tax_year_label}` : "";

  return (
    <div className={s.shell}>
      <a className={s.skip} href="#main">
        Skip to content
      </a>

      <header className={s.topbar}>
        <Link to="/" className={s.brand}>
          <Mark size={24} />
          LedgerLet
        </Link>
        <span>{yearLabel}</span>
      </header>

      <nav className={s.nav} aria-label="Main">
        <Link to="/" className={`${s.brand} ${s.navBrand}`} aria-label="LedgerLet, overview">
          <Mark />
          <span className={s.wordmark}>LedgerLet</span>
        </Link>
        <ul className={s.items}>
          {SECTIONS.map(({ to, label, Icon }) => (
            <li key={to}>
              <NavLink to={to} end={to === "/"} className={s.item}>
                <span className={s.pill}>
                  <Icon size={22} />
                </span>
                {label}
              </NavLink>
            </li>
          ))}
        </ul>
        <NavFooter yearLabel={yearLabel} />
      </nav>

      <main id="main" className={s.main} tabIndex={-1}>
        <div className={s.content}>
          <Outlet />
        </div>
      </main>
    </div>
  );
}

function NavFooter({ yearLabel }: { yearLabel: string }) {
  const me = useMe();
  const hmrc = useHmrcConnection();
  return (
    <div className={s.navFooter}>
      {yearLabel && <strong>{yearLabel}</strong>}
      {hmrc.data && (
        <span className={s.connected}>
          {hmrc.data.connected ? (
            <>
              <CheckIcon size={14} style={{ color: "var(--color-ledger)" }} />
              Connected to HMRC
            </>
          ) : (
            <Link to="/settings/hmrc">Connect to HMRC</Link>
          )}
        </span>
      )}
      {me.data && <span>{me.data.display_name ?? me.data.email}</span>}
      <button type="button" className={s.signOut} onClick={signOut}>
        Sign out
      </button>
    </div>
  );
}

/**
 * After moving to another page, put keyboard and screen reader focus on its
 * heading, so the change is announced and Tab starts from the top of the page.
 * Not on first load: the browser handles that.
 */
function useFocusHeadingOnNavigate() {
  const { pathname, state } = useLocation();
  const first = useRef(true);
  useEffect(() => {
    if (first.current) {
      first.current = false;
      // Arriving from the sign-in page: start at the top of the content, rather than
      // wherever the browser left focus when the sign-in form went away.
      if ((state as { signedIn?: boolean } | null)?.signedIn)
        document.getElementById("main")?.focus();
      return;
    }
    const heading = document.getElementById("page-heading") ?? document.getElementById("main");
    heading?.focus();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- only on page changes
  }, [pathname]);
}
