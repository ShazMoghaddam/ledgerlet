import { AlertIcon, CheckIcon } from "../../components/Icons";
import type { Check } from "./readiness";
import s from "./Tax.module.css";

/** Ticks for what's done, a warning for what's in the way, a dot for a note. Words carry it all. */
export function Checklist({ checks }: { checks: Check[] }) {
  return (
    <ul className={s.checks}>
      {checks.map((c) => (
        <li key={c.text} className={c.ok === false ? s.checkBad : undefined}>
          {c.ok === true ? (
            <CheckIcon size={18} />
          ) : c.ok === false ? (
            <AlertIcon size={18} />
          ) : (
            <span className={s.checkNeutral} aria-hidden="true" />
          )}
          {c.text}
        </li>
      ))}
    </ul>
  );
}
