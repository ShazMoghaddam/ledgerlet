import { useSyncExternalStore } from "react";

import { isSignedIn, subscribe } from "./session";

/** Whether someone is signed in, re-rendering when that changes. */
export function useSignedIn(): boolean {
  return useSyncExternalStore(subscribe, isSignedIn, () => false);
}

/** Only follow "next" links that stay inside the app. */
export function safeNext(next: string | null): string {
  return next && next.startsWith("/") && !next.startsWith("//") && !next.includes("\\")
    ? next
    : "/";
}
