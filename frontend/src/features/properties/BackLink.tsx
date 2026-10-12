import { Link } from "react-router";

import s from "./Properties.module.css";

export function BackLink({ to, children }: { to: string; children: string }) {
  return (
    <Link to={to} className={s.back}>
      <svg
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.2"
        aria-hidden="true"
      >
        <path d="M15 6l-6 6 6 6" />
      </svg>
      {children}
    </Link>
  );
}
