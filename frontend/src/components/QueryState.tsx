/** What a section shows while its data loads, or if loading fails. */
import { ApiError } from "../api/client";
import { Button } from "./Button";

export function Loading({ label }: { label: string }) {
  return (
    <p role="status" style={{ color: "var(--color-slate)" }}>
      Loading {label}…
    </p>
  );
}

export function LoadFailed({
  what,
  error,
  retry,
}: {
  what: string;
  error: unknown;
  retry?: () => void;
}) {
  const detail = error instanceof ApiError ? error.message : "The connection may have dropped.";
  return (
    <div role="alert" style={{ display: "grid", gap: "var(--space-2)", justifyItems: "start" }}>
      <p>
        <strong>Couldn’t load {what}.</strong> {detail}
      </p>
      {retry && (
        <Button variant="secondary" onClick={retry}>
          Try again
        </Button>
      )}
    </div>
  );
}
