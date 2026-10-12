import type { ReactNode } from "react";
import { Link } from "react-router";

import { Mark } from "../../components/Mark";
import { usePageTitle } from "../../hooks/usePageTitle";
import { formatLong } from "../../lib/dates";
import s from "./Legal.module.css";

/** Contact for privacy questions and data requests, shown on both pages. */
export const CONTACT_EMAIL = "shaz.moghaddam@gmail.com";

/**
 * The frame for the privacy notice and terms. Public: HMRC and anyone thinking of
 * signing up must be able to read them without an account.
 */
export function LegalPage({
  title,
  updated,
  children,
}: {
  title: string;
  updated: string; // ISO date
  children: ReactNode;
}) {
  usePageTitle(title);
  return (
    <div className={s.page}>
      <header className={s.top}>
        <Link to="/" className={s.brand}>
          <Mark size={24} />
          LedgerLet
        </Link>
      </header>
      <main id="main" className={s.main}>
        <article className={s.article}>
          <h1 id="page-heading" tabIndex={-1}>
            {title}
          </h1>
          <p className={s.updated}>Last updated {formatLong(updated)}</p>
          {children}
        </article>
      </main>
      <LegalFooter />
    </div>
  );
}

/** Used here and on the sign-in page. */
export function LegalFooter() {
  return (
    <footer className={s.footer}>
      <nav aria-label="Legal">
        <Link to="/privacy">Privacy</Link>
        <Link to="/terms">Terms</Link>
      </nav>
      <p>
        © 2026 LedgerLet. Built in London by{" "}
        <a href="https://shazmoghaddam.github.io/" rel="author">
          Shaz Moghaddam
        </a>
        .
      </p>
    </footer>
  );
}

export const Email = () => <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>;
