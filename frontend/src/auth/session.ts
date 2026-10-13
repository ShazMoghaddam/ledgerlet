/**
 * The signed-in session. LedgerLet never handles passwords: an identity provider
 * signs the landlord in and gives the browser an access token for the API.
 *
 * Two ways in, chosen when the app is built:
 * - Auth0, when VITE_AUTH0_DOMAIN, VITE_AUTH0_CLIENT_ID and VITE_AUTH0_AUDIENCE are
 *   set. The landlord signs in on Auth0's page (redirect, PKCE). Tokens are renewed
 *   with rotating refresh tokens, kept in this browser until signing out.
 * - A development token pasted on the sign-in page (scripts/dev_auth.py), kept in
 *   sessionStorage so it goes when the tab closes. Local development and tests only.
 *
 * Everything else asks this module three things: is someone signed in, what's the
 * token for the next request, and sign out. So the provider can change here alone.
 */
import type { Auth0Client } from "@auth0/auth0-spa-js";

const DEV_KEY = "ledgerlet.token";
const CALLBACK_PATH = "/sign-in/callback";

const auth0Config =
  import.meta.env.VITE_AUTH0_DOMAIN &&
  import.meta.env.VITE_AUTH0_CLIENT_ID &&
  import.meta.env.VITE_AUTH0_AUDIENCE
    ? {
        domain: import.meta.env.VITE_AUTH0_DOMAIN as string,
        clientId: import.meta.env.VITE_AUTH0_CLIENT_ID as string,
        audience: import.meta.env.VITE_AUTH0_AUDIENCE as string,
      }
    : null;

/** How this build signs people in. */
export const signInMethod: "auth0" | "dev-token" | "none" = auth0Config
  ? "auth0"
  : import.meta.env.DEV
    ? "dev-token"
    : "none";

type Listener = () => void;
const listeners = new Set<Listener>();
const notify = () => listeners.forEach((l) => l());

let auth0: Auth0Client | null = null;
let auth0SignedIn = false;

/** Called once before the app renders. With Auth0, finds out whether there's a session. */
export async function initSession(): Promise<void> {
  if (!auth0Config) return;
  const { createAuth0Client } = await import("@auth0/auth0-spa-js");
  auth0 = await createAuth0Client({
    domain: auth0Config.domain,
    clientId: auth0Config.clientId,
    authorizationParams: {
      audience: auth0Config.audience,
      redirect_uri: window.location.origin + CALLBACK_PATH,
    },
    cacheLocation: "localstorage", // survives a refresh; cleared on sign-out
    useRefreshTokens: true, // rotating, so a stolen refresh token stops working once used
    useRefreshTokensFallback: false,
  });
  auth0SignedIn = await auth0.isAuthenticated();
}

function readDevToken(): string | null {
  try {
    return sessionStorage.getItem(DEV_KEY);
  } catch {
    return null; // storage blocked: behave as signed out
  }
}

/** Is anyone signed in? Synchronous, for deciding what to show. */
export function isSignedIn(): boolean {
  return auth0 ? auth0SignedIn : readDevToken() !== null;
}

/** The token for the next API request, renewed if it's about to expire. */
export async function getAccessToken(): Promise<string | null> {
  if (!auth0) return readDevToken();
  if (!auth0SignedIn) return null;
  try {
    return (await auth0.getTokenSilently()) ?? null;
  } catch {
    // The session ended at Auth0 (expired, revoked, signed out elsewhere).
    await endSession();
    return null;
  }
}

/** Development only: sign in with a pasted token. */
export function signIn(token: string) {
  try {
    sessionStorage.setItem(DEV_KEY, token.trim());
  } finally {
    notify();
  }
}

/** Auth0: go to its sign-in page, coming back to `next` afterwards. */
export async function startSignIn(next: string): Promise<void> {
  if (!auth0) throw new Error("Auth0 isn't configured");
  await auth0.loginWithRedirect({ appState: { next } });
}

let finishing: Promise<string> | null = null;

/**
 * Auth0: back from its sign-in page. Returns where to go next. Runs once even if
 * React mounts the callback page twice: the code in the address can only be used once.
 */
export function finishSignIn(): Promise<string> {
  if (!auth0) return Promise.resolve("/");
  const client = auth0;
  finishing ??= client.handleRedirectCallback<{ next?: string }>().then(async (result) => {
    auth0SignedIn = await client.isAuthenticated();
    notify();
    return result.appState?.next ?? "/";
  });
  return finishing;
}

/** Forget the session here, without visiting the provider (e.g. after a 401). */
export async function endSession(): Promise<void> {
  try {
    sessionStorage.removeItem(DEV_KEY);
  } catch {
    // storage blocked: nothing stored
  }
  if (auth0) {
    auth0SignedIn = false;
    await auth0.logout({ openUrl: false }); // clears the stored tokens only
  }
  notify();
}

/** The landlord's own "Sign out": ends the provider's session too. */
export function signOut(): void {
  if (auth0) {
    auth0SignedIn = false;
    notify();
    void auth0.logout({ logoutParams: { returnTo: window.location.origin + "/sign-in" } });
    return;
  }
  void endSession();
}

export function subscribe(listener: Listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}
