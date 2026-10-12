import { Link } from "react-router";

import { Email, LegalPage } from "./LegalPage";
import s from "./Legal.module.css";

/** /terms: the terms of use, in plain English. */
export function TermsPage() {
  return (
    <LegalPage title="Terms of use" updated="2026-10-12">
      <div className={s.summary}>
        <strong>In short</strong>
        <ul>
          <li>LedgerLet helps you keep records and send your quarterly updates to HMRC.</li>
          <li>The figures you confirm and send are yours: check them before you send.</li>
          <li>LedgerLet isn’t tax advice, and isn’t made or endorsed by HMRC.</li>
        </ul>
      </div>

      <h2>Who we are</h2>
      <p>
        LedgerLet is provided by Shaz Moghaddam, trading as LedgerLet, in London (“we”, “us”). These
        terms apply when you use LedgerLet. Questions: <Email />.
      </p>

      <h2>What LedgerLet does</h2>
      <p>
        LedgerLet is software for Making Tax Digital for Income Tax. It keeps the income and
        expenses of the properties you let, works out your share, and, when you ask it to, sends
        your quarterly updates to HMRC.
      </p>
      <p>
        It isn’t tax, legal or accounting advice, and we aren’t your accountant. LedgerLet is
        independent: it isn’t made, endorsed or approved by HMRC. If you’re unsure how to treat
        something for tax, ask HMRC or a qualified adviser.
      </p>

      <h2>Your part</h2>
      <ul>
        <li>
          Keep your sign-in to yourself. You’re responsible for what’s done with your account.
        </li>
        <li>
          Record your income and expenses accurately, and put each in the right category. LedgerLet
          suggests categories, but you decide.
        </li>
        <li>
          Check your figures before you send an update. When you confirm and send, you’re telling
          HMRC the figures are correct and complete to the best of your knowledge.
        </li>
        <li>
          Meeting HMRC’s deadlines is your responsibility, and so are any penalties or tax due.
          Don’t leave sending until the last day, in case something goes wrong.
        </li>
        <li>Use LedgerLet only for your own tax affairs, and don’t try to break or misuse it.</li>
      </ul>

      <h2>Connecting to HMRC</h2>
      <p>
        When you connect, you give LedgerLet permission, at HMRC, to read and send your Making Tax
        Digital information. You can take that permission away at any time, in LedgerLet’s settings
        or with HMRC.
      </p>

      <h2>Your records</h2>
      <p>
        Your records stay yours. Making Tax Digital asks you to keep them for at least 5 years after
        the 31 January deadline for the tax year they belong to. If you stop using LedgerLet, ask us
        for a copy before you close your account. How we look after your data is set out in our{" "}
        <Link to="/privacy">privacy notice</Link>.
      </p>

      <h2>Availability and changes</h2>
      <p>
        We work to keep LedgerLet running and accurate, but we can’t promise it will always be
        available or free of errors. HMRC’s services can also be unavailable. We may change or
        improve LedgerLet, and we’ll tell you in advance about any change that significantly affects
        how you use it.
      </p>
      <p>
        LedgerLet is currently free to use. If that changes, we’ll tell you in advance, and you
        won’t be charged unless you agree.
      </p>

      <h2>Our responsibility to you</h2>
      <p>
        If we fail to provide LedgerLet with reasonable care and skill, you may have rights under
        the law, including the Consumer Rights Act 2015. Nothing in these terms takes those away, or
        limits our responsibility for death or personal injury caused by our negligence, or for
        fraud.
      </p>
      <p>
        Otherwise, we aren’t responsible for losses that weren’t a foreseeable result of something
        we did wrong, for figures you entered or confirmed, or for anything caused by events outside
        our reasonable control.
      </p>

      <h2>Ending</h2>
      <p>
        You can stop using LedgerLet at any time, and ask us to close your account. We may suspend
        or close an account that breaks these terms, and will tell you why unless the law stops us.
      </p>

      <h2>Changes to these terms, and the law</h2>
      <p>
        If we change these terms, we’ll update the date at the top and tell you in LedgerLet before
        the change applies. These terms are governed by the law of England and Wales. If you live
        elsewhere in the UK, you can also bring a claim in the courts where you live.
      </p>
    </LegalPage>
  );
}
