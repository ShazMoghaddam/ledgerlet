import { Link } from "react-router";

import { usePageTitle } from "../../hooks/usePageTitle";

export function NotFoundPage() {
  usePageTitle("Page not found");
  return (
    <div style={{ display: "grid", gap: "var(--space-4)" }}>
      <h1 id="page-heading" tabIndex={-1} style={{ fontSize: "var(--text-title)" }}>
        Page not found
      </h1>
      <p>
        Check the address, or go back to the <Link to="/">overview</Link>.
      </p>
    </div>
  );
}
