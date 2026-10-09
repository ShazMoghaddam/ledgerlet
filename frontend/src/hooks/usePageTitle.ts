import { useEffect } from "react";

/** Sets the browser tab title. The heading itself gets focus via PageHeading. */
export function usePageTitle(title: string) {
  useEffect(() => {
    document.title = title ? `${title} | LedgerLet` : "LedgerLet";
  }, [title]);
}
