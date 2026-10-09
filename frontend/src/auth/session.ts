/**
 * The signed-in session: just the bearer token the API checks.
 *
 * LedgerLet doesn't handle passwords. In production an identity provider signs the
 * landlord in and hands back a token; in development scripts/dev_auth.py makes one.
 * Either way this module only stores it and gives it to the API client.
 *
 * sessionStorage, not localStorage: the token goes when the tab closes. Swapping in
 * the chosen provider later only changes this file and the sign-in page.
 */

const KEY = "ledgerlet.token";
type Listener = () => void;
const listeners = new Set<Listener>();

function read(): string | null {
  try {
    return sessionStorage.getItem(KEY);
  } catch {
    return null; // storage blocked: behave as signed out
  }
}

export function getToken(): string | null {
  return read();
}

export function signIn(token: string) {
  try {
    sessionStorage.setItem(KEY, token.trim());
  } finally {
    listeners.forEach((l) => l());
  }
}

export function signOut() {
  try {
    sessionStorage.removeItem(KEY);
  } finally {
    listeners.forEach((l) => l());
  }
}

export function subscribe(listener: Listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}
