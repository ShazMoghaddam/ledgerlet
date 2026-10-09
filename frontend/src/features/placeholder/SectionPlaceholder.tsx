import { Link } from "react-router";

import { signOut } from "../../auth/session";
import { Button } from "../../components/Button";
import { usePageTitle } from "../../hooks/usePageTitle";

/** A section that's planned but not built yet. Honest about it, and still navigable. */
export function SectionPlaceholder({
  title,
  description,
  showSignOut = false,
}: {
  title: string;
  description: string;
  showSignOut?: boolean;
}) {
  usePageTitle(title);
  return (
    <div style={{ display: "grid", gap: "var(--space-4)", maxWidth: "36rem" }}>
      <h1 id="page-heading" tabIndex={-1} style={{ fontSize: "var(--text-title)" }}>
        {title}
      </h1>
      <p style={{ color: "var(--color-slate)" }}>{description}</p>
      {showSignOut && (
        <div>
          <Button variant="secondary" onClick={signOut}>
            Sign out
          </Button>
        </div>
      )}
    </div>
  );
}

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
