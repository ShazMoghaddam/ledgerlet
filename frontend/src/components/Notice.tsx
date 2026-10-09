import { CheckIcon } from "./Icons";

/** Confirms that something worked ("Transaction added."). Announced politely. */
export function Notice({ children }: { children: string }) {
  return (
    <p
      role="status"
      style={{
        display: "flex",
        alignItems: "center",
        gap: "var(--space-2)",
        padding: "var(--space-3) var(--space-4)",
        borderRadius: "var(--radius-control)",
        background: "var(--color-ledger-tint)",
        color: "var(--color-ledger)",
        fontWeight: 600,
      }}
    >
      <CheckIcon size={18} />
      {children}
    </p>
  );
}
