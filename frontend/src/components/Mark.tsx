/** LedgerLet's mark: two ledger lines. Decorative; the wordmark or a label names it. */
export function Mark({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true" focusable="false">
      <rect width="32" height="32" rx="6" fill="var(--color-ledger)" />
      <path d="M9 8v16h14" fill="none" stroke="#fff" strokeWidth="3" strokeLinecap="square" />
      <path
        d="M14 8v11h9"
        fill="none"
        stroke="#fff"
        strokeWidth="3"
        strokeLinecap="square"
        opacity=".55"
      />
    </svg>
  );
}
