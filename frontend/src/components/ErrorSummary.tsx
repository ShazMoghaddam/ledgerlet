import { useEffect, useRef } from "react";

import s from "./ErrorSummary.module.css";

export interface FieldError {
  field?: string; // the id of the control to jump to
  message: string;
}

/**
 * All of a form's problems in one place, at the top, focused when it appears so
 * screen reader and keyboard users land on it. Each links to its field.
 */
export function ErrorSummary({ errors }: { errors: FieldError[] }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (errors.length) ref.current?.focus();
  }, [errors]);
  if (!errors.length) return null;
  return (
    <div
      ref={ref}
      className={s.summary}
      role="alert"
      tabIndex={-1}
      aria-labelledby="error-summary-title"
    >
      <h2 id="error-summary-title">There’s a problem</h2>
      <ul>
        {errors.map((e) => (
          <li key={`${e.field ?? "form"}-${e.message}`}>
            {e.field ? (
              <a
                href={`#${e.field}`}
                onClick={(event) => {
                  event.preventDefault();
                  document.getElementById(e.field!)?.focus();
                }}
              >
                {e.message}
              </a>
            ) : (
              e.message
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
