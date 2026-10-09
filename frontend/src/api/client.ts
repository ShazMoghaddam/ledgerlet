/**
 * The one way the app talks to the API. Paths, parameters and responses are all
 * typed from the backend's own OpenAPI description, so a backend change that the
 * frontend doesn't handle fails the type check instead of failing in the browser.
 */
import createClient, { type Middleware } from "openapi-fetch";

import { getToken, signOut } from "../auth/session";
import { deviceHeader } from "./device";
import type { paths } from "./schema";

const auth: Middleware = {
  onRequest({ request }) {
    const token = getToken();
    if (token) request.headers.set("Authorization", `Bearer ${token}`);
    if (new URL(request.url).pathname.startsWith("/api/v1/hmrc/")) {
      request.headers.set("X-LedgerLet-Device", deviceHeader());
    }
    return request;
  },
  onResponse({ response }) {
    // Expired or invalid sign-in: drop it, and the app shows the sign-in page.
    if (response.status === 401) signOut();
    return response;
  },
};

export const api = createClient<paths>({
  baseUrl: window.location.origin,
  // Look fetch up on each call (not once at start-up), so test mocks can stand in for it.
  fetch: (request) => globalThis.fetch(request),
});
api.use(auth);

/** An API failure, with the server's own message when it sent one. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/** Unwrap an openapi-fetch result: the data, or an ApiError. */
export function unwrap<T>(result: { data?: T; error?: unknown; response: Response }): T {
  if (result.data !== undefined) return result.data;
  const detail = (result.error as { detail?: unknown } | undefined)?.detail;
  const message =
    typeof detail === "string" ? detail : `Request failed (${result.response.status})`;
  throw new ApiError(result.response.status, message);
}
