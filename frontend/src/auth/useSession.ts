import { useSyncExternalStore } from "react";

import { getToken, subscribe } from "./session";

/** The current token, re-rendering when the landlord signs in or out. */
export function useToken(): string | null {
  return useSyncExternalStore(subscribe, getToken, () => null);
}

/** Only follow "next" links that stay inside the app. */
export function safeNext(next: string | null): string {
  return next && next.startsWith("/") && !next.startsWith("//") && !next.includes("\\")
    ? next
    : "/";
}
