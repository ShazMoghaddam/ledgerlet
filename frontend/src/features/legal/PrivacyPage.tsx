import { Link } from "react-router";

import { Email, LegalPage } from "./LegalPage";
import s from "./Legal.module.css";

/**
 * /privacy: the privacy notice. Written for the landlord, and kept true to what the
 * code actually stores and sends: if that changes, this page changes with it.
 */
export function PrivacyPage() {
  return (
    <LegalPage title="Privacy notice" updated="2026-10-12">
      <div className={s.summary}>
        <strong>In short</strong>
        <ul>
          <li>
            We keep the records you put into LedgerLet so we can work out and send your updates.
          </li>
          <li>We share them with HMRC only when you send an update, and only what HMRC needs.</li>
          <li>We don’t sell your data, show you adverts, or use tracking or analytics cookies.</li>
        </ul>
      </div>

      <h2>Who we are</h2>
      <p>
        LedgerLet is provided by Shaz Moghaddam, trading as LedgerLet, in London. We are the data
        controller for the personal data described here. For anything about your data, email{" "}
        <Email />.
      </p>

      <h2>What we collect, and why</h2>
      <h3>Your account</h3>
      <p>
        When you sign in, we keep an identifier from your sign-in provider, your email address if it
        shares one, and the name and settings you choose (such as how your quarters run). We use
        these to know it’s you and to show you your own records.
      </p>
      <h3>Your properties and transactions</h3>
      <p>
        The properties you let (name, address, postcode and your share), and the income and expenses
        you record or import (date, description, amount and category). These are the records Making
        Tax Digital asks you to keep, and LedgerLet needs them to work out your quarterly figures.
      </p>
      <p>
        When you import a bank statement, LedgerLet reads the file to show you its rows. The file
        itself isn’t stored: only the rows you choose to import, and a short code for each so the
        same row isn’t imported twice.
      </p>
      <h3>Your HMRC details</h3>
      <p>
        Your National Insurance number, which we store encrypted and only ever show in part; your
        HMRC business ID for your property income; and the permission HMRC gives LedgerLet when you
        connect, also stored encrypted. We never see or store your HMRC password.
      </p>
      <h3>What you send to HMRC</h3>
      <p>
        Each update you send, HMRC’s answer and its reference, so you have a record of what HMRC
        received and when.
      </p>
      <h3>Fraud prevention information</h3>
      <p>
        HMRC requires software to send information about the device and connection used with each
        request to its services, to help prevent fraud. For LedgerLet that’s: your IP address, a
        random ID for your browser, your browser’s description of itself, your screen and window
        sizes, your time zone, and your LedgerLet account ID. We send it to HMRC with each request
        to HMRC and don’t keep it for anything else.
      </p>

      <h2>Our lawful bases</h2>
      <ul>
        <li>
          <strong>Contract:</strong> to provide LedgerLet to you: keep your records, work out your
          figures and send the updates you ask us to.
        </li>
        <li>
          <strong>Legal obligation:</strong> to send HMRC the fraud prevention information it
          requires.
        </li>
        <li>
          <strong>Legitimate interests:</strong> to keep LedgerLet secure and working, for example
          by investigating errors.
        </li>
      </ul>

      <h2>Who we share it with</h2>
      <ul>
        <li>
          <strong>HMRC</strong>, when you connect LedgerLet and when you send an update. HMRC then
          uses it under its own privacy notice.
        </li>
        <li>
          <strong>Our service providers</strong>: the company that hosts LedgerLet and stores its
          data, and the company that runs sign-in. They may only use your data to provide their
          service to us. We’ll name them on this page before LedgerLet opens to the public.
        </li>
      </ul>
      <p>
        We aim to keep your data in the UK. If a provider stores any of it elsewhere, it will be
        protected by UK adequacy regulations or the safeguards the Information Commissioner’s Office
        approves, and this page will say so.
      </p>

      <h2>In your browser</h2>
      <p>LedgerLet stores three small things in your browser, all needed for it to work:</p>
      <ul>
        <li>your sign-in, which is removed when you close the tab;</li>
        <li>
          the random browser ID HMRC asks for (see above), kept so it stays the same each time;
        </li>
        <li>a cookie while you connect to HMRC, which lasts at most 10 minutes.</li>
      </ul>
      <p>There are no advertising, tracking or analytics cookies.</p>

      <h2>How long we keep it</h2>
      <p>
        We keep your records while you have an account. Making Tax Digital asks you to keep your
        records for at least 5 years after the 31 January deadline for the tax year they belong to,
        so before you close your account, ask us for a copy if you need one.
      </p>
      <p>
        When you close your account, we delete your data within 30 days, unless the law requires us
        to keep something longer. To close your account, email <Email />.
      </p>

      <h2>Your rights</h2>
      <p>
        You can ask us for a copy of your data, to correct it, to delete it, to limit how we use it,
        to give it to you in a form another service can use, or to stop using it where we rely on
        legitimate interests. Email <Email /> and we’ll reply within one month.
      </p>
      <p>
        If you’re unhappy with how we’ve handled your data, please tell us first. You can also
        complain to the Information Commissioner’s Office at{" "}
        <a href="https://ico.org.uk/make-a-complaint/">ico.org.uk/make-a-complaint</a> or on 0303
        123 1113.
      </p>

      <h2>Keeping it safe</h2>
      <p>
        Your connection to LedgerLet is encrypted. Your National Insurance number and HMRC
        permission are encrypted again where they’re stored. Each landlord can only ever see their
        own records.
      </p>

      <h2>Changes</h2>
      <p>
        If we change this notice, we’ll update the date at the top, and tell you in LedgerLet before
        any change that affects how your data is used. See also our{" "}
        <Link to="/terms">terms of use</Link>.
      </p>
    </LegalPage>
  );
}
