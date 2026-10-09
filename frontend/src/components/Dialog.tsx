import { useEffect, useRef, type ReactNode } from "react";

import s from "./Dialog.module.css";

/**
 * A modal built on the browser's own <dialog>: it traps focus, closes on Escape,
 * returns focus to whatever opened it, and hides the page behind from screen readers.
 * "sheet" slides up from the bottom on phones (used for filters).
 */
export function Dialog({
  open,
  onClose,
  title,
  children,
  variant = "dialog",
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  variant?: "dialog" | "sheet";
}) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  return (
    <dialog
      ref={ref}
      className={`${s.dialog} ${variant === "sheet" ? s.sheet : ""}`}
      aria-labelledby="dialog-title"
      onClose={onClose}
      onCancel={(e) => {
        e.preventDefault();
        onClose();
      }}
    >
      {open && (
        <div className={s.body}>
          <h2 id="dialog-title" className={s.title}>
            {title}
          </h2>
          {children}
        </div>
      )}
    </dialog>
  );
}
